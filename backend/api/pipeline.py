"""
pipeline.py — Orchestrates the full RAG processing pipeline.

Runs in a background thread triggered by POST /api/process/.
Steps:
  1. Parse CSV → Message objects (bulk create)
  2. Detect topic changes → TopicCheckpoint objects
  3. Create 100-message checkpoints → HundredCheckpoint objects
  4. Build FAISS embeddings index
  5. Extract persona → Persona object
  6. Update ProcessingStatus throughout
"""

import json
import logging
import threading
import traceback
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_processing_lock = threading.Lock()


def run_pipeline_background():
    """Start the pipeline in a background thread."""
    if not _processing_lock.acquire(blocking=False):
        logger.warning("Pipeline is already running.")
        return False

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()
    return True


def _run_pipeline():
    """The actual pipeline execution."""
    from django.conf import settings
    from api.models import (Message, TopicCheckpoint, HundredCheckpoint,
                             ProcessingStatus)
    from api.rag_engine.preprocessor import parse_csv
    from api.rag_engine.topic_detector import detect_topics, get_top_keywords
    from api.rag_engine.summarizer import summarize_messages, summarize_for_hundred_checkpoint
    from api.rag_engine.embedder import build_faiss_index
    from api.persona.extractor import extract_persona
    from api.persona.store import save_persona, save_persona_to_db

    status = _get_or_create_status()

    try:
        # ── Step 0: Reset ──────────────────────────────────────────────────
        status.status = 'processing'
        status.started_at = datetime.now(timezone.utc)
        status.progress_pct = 0.0
        status.error_message = ''
        status.save()

        Message.objects.all().delete()
        TopicCheckpoint.objects.all().delete()
        HundredCheckpoint.objects.all().delete()

        # ── Step 1: Parse CSV ──────────────────────────────────────────────
        _update_status(status, 2.0, "Parsing CSV file...")
        csv_path = str(settings.CSV_PATH)
        messages = parse_csv(csv_path)

        if not messages:
            raise ValueError("No messages parsed from CSV!")

        _update_status(status, 15.0, f"Saving {len(messages)} messages to database...")

        # Bulk create messages
        BATCH = 5000
        msg_objects = [
            Message(
                conversation_id=m['conversation_id'],
                global_index=m['global_index'],
                speaker=m['speaker'],
                text=m['text'],
            )
            for m in messages
        ]
        for i in range(0, len(msg_objects), BATCH):
            Message.objects.bulk_create(msg_objects[i:i + BATCH])
            pct = 15.0 + (i / len(msg_objects)) * 15.0
            _update_status(status, pct, f"Saved {min(i+BATCH, len(msg_objects))}/{len(messages)} messages...")

        status.total_messages = len(messages)
        status.save()

        # ── Step 2: Topic Detection ────────────────────────────────────────
        _update_status(status, 30.0, "Detecting topic changes...")
        segments = detect_topics(messages)

        _update_status(status, 40.0, f"Generating summaries for {len(segments)} topics...")
        topic_objects = []
        for i, seg in enumerate(segments):
            seg_messages = seg['messages']
            summary = summarize_messages(seg_messages, max_sentences=4)
            keywords = get_top_keywords([m['text'] for m in seg_messages])
            day_start = min(m['conversation_id'] for m in seg_messages)
            day_end = max(m['conversation_id'] for m in seg_messages)

            topic_objects.append(TopicCheckpoint(
                topic_number=i + 1,
                start_global_index=seg['start'],
                end_global_index=seg['end'],
                conversation_day_start=day_start,
                conversation_day_end=day_end,
                summary=summary,
                keywords=json.dumps(keywords),
            ))

            if i % 50 == 0:
                pct = 40.0 + (i / len(segments)) * 15.0
                _update_status(status, pct, f"Summarized {i}/{len(segments)} topics...")

        TopicCheckpoint.objects.bulk_create(topic_objects)
        status.total_topics = len(topic_objects)
        status.save()
        logger.info(f"Created {len(topic_objects)} topic checkpoints")

        # ── Step 3: 100-Message Checkpoints ───────────────────────────────
        _update_status(status, 55.0, "Creating 100-message checkpoints...")
        hundred_objects = []
        HUNDRED = 100
        for i in range(0, len(messages), HUNDRED):
            chunk = messages[i:i + HUNDRED]
            summary = summarize_for_hundred_checkpoint(chunk)
            hundred_objects.append(HundredCheckpoint(
                checkpoint_number=(i // HUNDRED) + 1,
                start_global_index=chunk[0]['global_index'],
                end_global_index=chunk[-1]['global_index'],
                summary=summary,
            ))

        HundredCheckpoint.objects.bulk_create(hundred_objects)
        status.total_checkpoints = len(hundred_objects)
        status.save()
        logger.info(f"Created {len(hundred_objects)} 100-message checkpoints")

        # ── Step 4: Build FAISS Index ──────────────────────────────────────
        _update_status(status, 60.0, "Building embedding index (this may take several minutes)...")
        build_faiss_index(
            messages,
            str(settings.FAISS_INDEX_PATH),
            str(settings.FAISS_META_PATH),
        )
        _update_status(status, 85.0, "Embedding index built.")

        # ── Step 5: Persona Extraction ─────────────────────────────────────
        _update_status(status, 87.0, "Extracting user persona...")
        from api.persona.extractor import extract_persona
        persona = extract_persona(messages)
        save_persona(persona, str(settings.PERSONA_PATH))
        save_persona_to_db(persona)
        _update_status(status, 95.0, "Persona saved.")

        # ── Done ───────────────────────────────────────────────────────────
        status.status = 'done'
        status.progress_pct = 100.0
        status.current_step = 'Processing complete!'
        status.finished_at = datetime.now(timezone.utc)
        status.save()
        logger.info("Pipeline complete!")

    except Exception as e:
        logger.error(f"Pipeline error: {e}\n{traceback.format_exc()}")
        status.status = 'error'
        status.error_message = str(e)
        status.save()
    finally:
        _processing_lock.release()


def _get_or_create_status():
    from api.models import ProcessingStatus
    obj, _ = ProcessingStatus.objects.get_or_create(pk=1)
    return obj


def _update_status(status, pct: float, step: str):
    status.progress_pct = pct
    status.current_step = step
    status.save()
    logger.info(f"[{pct:.1f}%] {step}")

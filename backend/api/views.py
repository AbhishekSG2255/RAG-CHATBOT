"""
API Views for RAG Chatbot.

Endpoints:
  POST /api/process/       — Start background CSV processing
  GET  /api/status/        — Get processing status
  POST /api/chat/          — Ask a question (RAG answer)
  GET  /api/persona/       — Get persona JSON
  GET  /api/topics/        — List topic checkpoints (paginated)
  GET  /api/checkpoints/   — List 100-msg checkpoints (paginated)
  GET  /api/stats/         — Overall stats
"""

import json
import logging
import os

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (Message, TopicCheckpoint, HundredCheckpoint,
                     Persona, ProcessingStatus)
from .serializers import (TopicCheckpointSerializer, HundredCheckpointSerializer,
                           PersonaSerializer, ProcessingStatusSerializer)
from .pipeline import run_pipeline_background

logger = logging.getLogger(__name__)

# Global FAISS cache — load once after processing
_faiss_cache = {'index': None, 'meta': None, 'loaded': False}


def _get_faiss():
    """Lazy-load FAISS index from disk."""
    if not _faiss_cache['loaded']:
        from .rag_engine.embedder import load_faiss_index
        idx, meta = load_faiss_index(
            str(settings.FAISS_INDEX_PATH),
            str(settings.FAISS_META_PATH),
        )
        _faiss_cache['index'] = idx
        _faiss_cache['meta'] = meta
        _faiss_cache['loaded'] = True
    return _faiss_cache['index'], _faiss_cache['meta']


class ProcessView(APIView):
    """POST /api/process/ — Trigger CSV processing pipeline."""

    def post(self, request):
        # Check if already done
        try:
            s = ProcessingStatus.objects.get(pk=1)
            if s.status == 'processing':
                return Response({'message': 'Pipeline is already running.',
                                 'status': 'processing'}, status=status.HTTP_200_OK)
        except ProcessingStatus.DoesNotExist:
            pass

        started = run_pipeline_background()
        if started:
            return Response({'message': 'Processing started in background.',
                             'status': 'started'}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'message': 'Pipeline is already running.',
                             'status': 'running'}, status=status.HTTP_200_OK)

    def get(self, request):
        """GET also works — returns current status."""
        return self.get_status()

    def get_status(self):
        try:
            s = ProcessingStatus.objects.get(pk=1)
            return Response(ProcessingStatusSerializer(s).data)
        except ProcessingStatus.DoesNotExist:
            return Response({'status': 'idle', 'progress_pct': 0})


class StatusView(APIView):
    """GET /api/status/ — Get current processing status."""

    def get(self, request):
        try:
            s = ProcessingStatus.objects.get(pk=1)
            return Response(ProcessingStatusSerializer(s).data)
        except ProcessingStatus.DoesNotExist:
            return Response({
                'status': 'idle',
                'current_step': 'Not started',
                'progress_pct': 0.0,
                'total_messages': 0,
                'total_topics': 0,
                'total_checkpoints': 0,
                'error_message': '',
            })


class ChatView(APIView):
    """POST /api/chat/ — Main RAG chatbot endpoint."""

    def post(self, request):
        query = request.data.get('query', '').strip()
        history = request.data.get('history', [])
        if not query:
            return Response({'error': 'query is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Check processing is done
        try:
            proc = ProcessingStatus.objects.get(pk=1)
            if proc.status not in ('done',):
                return Response({
                    'error': 'Data is not processed yet. Please run POST /api/process/ first.',
                    'processing_status': proc.status,
                    'progress_pct': proc.progress_pct,
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ProcessingStatus.DoesNotExist:
            return Response({'error': 'Please run POST /api/process/ first.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Check for persona-related questions and answer from persona
        persona_data = _load_persona()
        if persona_data:
            persona_answer = _try_persona_answer(query, persona_data)
            if persona_answer:
                return Response({
                    'answer': persona_answer,
                    'answer_mode': 'persona',
                    'sources': {'type': 'persona'},
                    'query': query,
                })

        # RAG retrieval
        try:
            faiss_index, chunk_meta = _get_faiss()
            topic_summaries = list(
                TopicCheckpoint.objects.values(
                    'topic_number', 'start_global_index', 'end_global_index',
                    'summary', 'keywords'
                )
            )
            hundred_summaries = list(
                HundredCheckpoint.objects.values(
                    'checkpoint_number', 'start_global_index', 'end_global_index', 'summary'
                )
            )

            from .rag_engine.retriever import retrieve_and_answer
            result = retrieve_and_answer(
                query=query,
                faiss_index=faiss_index,
                chunk_meta=chunk_meta or [],
                topic_summaries=topic_summaries,
                hundred_summaries=hundred_summaries,
                messages_db=Message,
                groq_api_key=settings.GROQ_API_KEY,
                history=history,
            )

            return Response({
                'answer': result['answer'],
                'answer_mode': result.get('answer_mode', 'extractive'),
                'sources': result['sources'],
                'query': query,
            })

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return Response({'error': f'Failed to generate answer: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonaView(APIView):
    """GET /api/persona/ — Return the full persona JSON."""

    def get(self, request):
        persona_data = _load_persona()
        if not persona_data:
            return Response({'error': 'Persona not yet extracted. Run /api/process/ first.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(persona_data)


class TopicsView(APIView):
    """GET /api/topics/ — List topic checkpoints with pagination."""

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        search = request.query_params.get('search', '')

        qs = TopicCheckpoint.objects.all()
        if search:
            qs = qs.filter(summary__icontains=search) | qs.filter(keywords__icontains=search)

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        topics = qs[start:end]

        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': max(1, (total + page_size - 1) // page_size),
            'results': TopicCheckpointSerializer(topics, many=True).data,
        })


class CheckpointsView(APIView):
    """GET /api/checkpoints/ — List 100-message checkpoints."""

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        qs = HundredCheckpoint.objects.all()
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        checkpoints = qs[start:end]

        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': max(1, (total + page_size - 1) // page_size),
            'results': HundredCheckpointSerializer(checkpoints, many=True).data,
        })


class StatsView(APIView):
    """GET /api/stats/ — Overall stats."""

    def get(self, request):
        try:
            proc = ProcessingStatus.objects.get(pk=1)
            proc_data = ProcessingStatusSerializer(proc).data
        except ProcessingStatus.DoesNotExist:
            proc_data = {'status': 'idle'}

        return Response({
            'processing': proc_data,
            'counts': {
                'messages': Message.objects.count(),
                'topics': TopicCheckpoint.objects.count(),
                'checkpoints': HundredCheckpoint.objects.count(),
            }
        })


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_persona() -> dict:
    """Load persona from DB or JSON file."""
    try:
        from api.persona.store import load_persona_from_db
        data = load_persona_from_db()
        if data:
            return data
    except Exception:
        pass
    # Fallback to JSON file
    try:
        from api.persona.store import load_persona
        return load_persona(str(settings.PERSONA_PATH))
    except Exception:
        return {}


def _try_persona_answer(query: str, persona_data: dict) -> str:
    """Try to answer directly from persona data for common questions."""
    q = query.lower()

    target_speaker = "User 1"
    if "user 2" in q:
        target_speaker = "User 2"

    if target_speaker not in persona_data and "habits" in persona_data:
        # Fallback to old format
        persona = persona_data
    else:
        persona = persona_data.get(target_speaker, {})

    if not persona:
        return ""

    if any(w in q for w in ['habit', 'routine', 'daily', 'sleep', 'eat', 'food']):
        habits = persona.get('habits', [])
        if habits:
            return (
                f"Based on the conversations, here are {target_speaker}'s habits and routines:\n\n"
                + "\n".join(f"• {h}" for h in habits)
            )

    if any(w in q for w in ['who', 'person', 'kind', 'personality', 'character', 'like', 'type of']):
        summary = persona.get('summary', '')
        personality = persona.get('personality', {})
        traits = personality.get('key_traits', [])
        tone = personality.get('overall_tone', '')
        humor = personality.get('humor', '')

        answer = f"Based on the conversations, here's what kind of person {target_speaker} appears to be:\n\n"
        if summary:
            answer += f"{summary}\n\n"
        if traits:
            answer += f"**Key traits:** {', '.join(traits)}\n"
        if tone:
            answer += f"**Overall tone:** {tone}\n"
        if humor:
            answer += f"**Humor:** {humor}\n"
        return answer

    if any(w in q for w in ['talk', 'speak', 'communicate', 'style', 'write', 'message']):
        style = persona.get('communication_style', {})
        if style:
            answer = f"Here's how {target_speaker} communicates:\n\n"
            for key, val in style.items():
                if key != 'common_phrases':
                    answer += f"• **{key.replace('_', ' ').title()}**: {val}\n"
            phrases = style.get('common_phrases', [])
            if phrases:
                answer += f"\n**Common phrases:** {', '.join(phrases[:3])}"
            return answer

    if any(w in q for w in ['interest', 'hobby', 'hobbies', 'enjoy', 'fun']):
        facts = persona.get('personal_facts', {})
        hobbies = facts.get('hobbies', [])
        if hobbies:
            return (
                f"Based on the conversations, here are {target_speaker}'s interests and hobbies:\n\n"
                + "\n".join(f"• {h.title()}" for h in hobbies)
            )

    if any(w in q for w in ['job', 'work', 'occupation', 'career', 'profession', 'do for']):
        facts = persona.get('personal_facts', {})
        occs = facts.get('likely_occupations', [])
        if occs:
            return (
                f"Based on mentions in conversations, {target_speaker}'s likely occupations include:\n\n"
                + "\n".join(f"• {o.title()}" for o in occs)
            )

    return ""  # No direct persona match — fall through to RAG

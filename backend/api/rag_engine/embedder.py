"""
embedder.py — Sentence embeddings with sentence-transformers + FAISS index.

Uses 'all-MiniLM-L6-v2' (~80MB) — fast and accurate, runs fully locally.
Embeds message chunks (groups of CHUNK_SIZE messages) and stores them in
a FAISS flat L2 index serialized to disk.

Index metadata (chunk → message range mapping) is stored as JSON.
"""

import json
import logging
import numpy as np
import os

logger = logging.getLogger(__name__)

CHUNK_SIZE = 8  # Messages per embedding chunk
MODEL_NAME = 'all-MiniLM-L6-v2'

_model = None  # Lazy-loaded


def _get_model():
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded.")
    return _model


def build_faiss_index(messages: list[dict], index_path: str, meta_path: str):
    """
    Build a FAISS index from all messages.

    Each "document" in the index is a chunk of CHUNK_SIZE consecutive messages.
    The metadata JSON maps each FAISS index position → chunk info.
    """
    import faiss

    model = _get_model()
    n = len(messages)
    logger.info(f"Building FAISS index for {n} messages in chunks of {CHUNK_SIZE}...")

    chunks = []
    chunk_meta = []

    for i in range(0, n, CHUNK_SIZE):
        chunk = messages[i:i + CHUNK_SIZE]
        chunk_text = ' '.join([m['text'] for m in chunk])
        chunks.append(chunk_text)
        chunk_meta.append({
            'chunk_idx': len(chunk_meta),
            'start_global': chunk[0]['global_index'],
            'end_global': chunk[-1]['global_index'],
            'start_conv': chunk[0]['conversation_id'],
            'preview': chunk_text[:200],
        })

        if len(chunks) % 500 == 0:
            logger.info(f"  Embedded {len(chunks)} chunks so far...")

    logger.info(f"Encoding {len(chunks)} chunks with sentence-transformers...")
    embeddings = model.encode(chunks, batch_size=64, show_progress_bar=True,
                              convert_to_numpy=True)
    embeddings = embeddings.astype(np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Save index
    faiss.write_index(index, index_path)
    logger.info(f"FAISS index saved to {index_path}")

    # Save metadata
    with open(meta_path, 'w') as f:
        json.dump(chunk_meta, f)
    logger.info(f"FAISS metadata saved to {meta_path}")

    return index, chunk_meta


def load_faiss_index(index_path: str, meta_path: str):
    """Load an existing FAISS index and metadata from disk."""
    import faiss
    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        return None, None
    index = faiss.read_index(index_path)
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    return index, meta


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string."""
    model = _get_model()
    vec = model.encode([query], convert_to_numpy=True).astype(np.float32)
    return vec

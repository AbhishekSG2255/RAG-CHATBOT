"""
summarizer.py — Extractive summarization (no external LLM needed).

Uses TF-IDF sentence scoring to pick the most representative sentences
from a block of messages. Falls back to simple first-N sentences if needed.
"""

import re
import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


def summarize_messages(messages: list[dict], max_sentences: int = 4) -> str:
    """
    Generate an extractive summary from a list of message dicts.
    Picks the most important sentences using TF-IDF scoring.
    """
    if not messages:
        return ""

    texts = [m['text'] for m in messages]
    combined = ' '.join(texts)

    # Split into sentences
    sentences = _split_sentences(combined)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

    if len(sentences) <= max_sentences:
        return ' '.join(sentences)

    try:
        return _textrank_summary(sentences, max_sentences)
    except Exception as e:
        logger.warning(f"TextRank failed: {e}, using first sentences")
        return ' '.join(sentences[:max_sentences])


def _split_sentences(text: str) -> list[str]:
    """Simple sentence splitter."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s for s in sentences if s.strip()]


def _textrank_summary(sentences: list[str], n: int) -> str:
    """
    TextRank-inspired extractive summary:
    1. Compute TF-IDF vectors for each sentence.
    2. Build similarity matrix between sentences.
    3. Score sentences by sum of similarities (PageRank-like).
    4. Return top-n sentences in original order.
    """
    if len(sentences) < 2:
        return sentences[0] if sentences else ""

    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        tfidf = vectorizer.fit_transform(sentences)
    except ValueError:
        return ' '.join(sentences[:n])

    sim_matrix = cosine_similarity(tfidf, tfidf)
    np.fill_diagonal(sim_matrix, 0)

    # Score = sum of similarities to all other sentences
    scores = sim_matrix.sum(axis=1)

    # Pick top-n by score, then sort back to original order
    ranked_indices = np.argsort(scores)[-n:]
    ranked_indices = sorted(ranked_indices)

    return ' '.join([sentences[i] for i in ranked_indices])


def summarize_for_hundred_checkpoint(messages: list[dict]) -> str:
    """Summary for 100-message checkpoints — slightly more concise."""
    return summarize_messages(messages, max_sentences=5)

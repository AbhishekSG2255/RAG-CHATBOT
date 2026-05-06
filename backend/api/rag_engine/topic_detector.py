"""
topic_detector.py — Detect topic changes using TF-IDF cosine similarity.

Algorithm:
  1. Group messages into sliding windows of WINDOW_SIZE.
  2. Compute TF-IDF vector for each window.
  3. Compare consecutive windows using cosine similarity.
  4. When similarity < THRESHOLD → topic has changed → create checkpoint.
  5. Each topic segment gets a summary via summarizer.py.

This approach requires NO external API or LLM.
"""

import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Tunable parameters
WINDOW_SIZE = 15          # Number of messages per window for comparison
STEP_SIZE = 5             # How many messages to advance the window each time
SIMILARITY_THRESHOLD = 0.25  # Below this → topic changed
MIN_TOPIC_LENGTH = 10     # Minimum messages to constitute a topic


def detect_topics(messages: list[dict]) -> list[dict]:
    """
    Detect topic segments from a list of message dicts.

    Returns:
        list of {
            'start': int,       # global_index of first message
            'end': int,         # global_index of last message
            'messages': list,   # message dicts in this segment
        }
    """
    if not messages:
        return []

    texts = [m['text'] for m in messages]
    n = len(texts)

    if n < WINDOW_SIZE:
        return [{'start': messages[0]['global_index'],
                 'end': messages[-1]['global_index'],
                 'messages': messages}]

    logger.info(f"Detecting topics in {n} messages...")

    # Build TF-IDF for all windows
    vectorizer = TfidfVectorizer(
        stop_words='english',
        max_features=3000,
        ngram_range=(1, 2),
        min_df=1,
    )

    # Create window texts
    window_texts = []
    window_positions = []
    for i in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
        window = ' '.join(texts[i:i + WINDOW_SIZE])
        window_texts.append(window)
        window_positions.append(i)

    if len(window_texts) < 2:
        return [{'start': messages[0]['global_index'],
                 'end': messages[-1]['global_index'],
                 'messages': messages}]

    try:
        tfidf_matrix = vectorizer.fit_transform(window_texts)
    except Exception as e:
        logger.warning(f"TF-IDF failed: {e}, returning single topic")
        return [{'start': messages[0]['global_index'],
                 'end': messages[-1]['global_index'],
                 'messages': messages}]

    # Compute similarity between consecutive windows
    topic_boundaries = [0]  # message indices where new topics start

    for i in range(len(window_texts) - 1):
        sim = cosine_similarity(tfidf_matrix[i], tfidf_matrix[i + 1])[0][0]
        if sim < SIMILARITY_THRESHOLD:
            # Map window position back to message index
            boundary = window_positions[i + 1]
            # Only add if sufficiently far from last boundary
            if boundary - topic_boundaries[-1] >= MIN_TOPIC_LENGTH:
                topic_boundaries.append(boundary)

    topic_boundaries.append(n)  # end sentinel

    # Build topic segments
    segments = []
    for i in range(len(topic_boundaries) - 1):
        start_idx = topic_boundaries[i]
        end_idx = topic_boundaries[i + 1]
        seg_messages = messages[start_idx:end_idx]
        if seg_messages:
            segments.append({
                'start': seg_messages[0]['global_index'],
                'end': seg_messages[-1]['global_index'],
                'messages': seg_messages,
            })

    logger.info(f"Detected {len(segments)} topics")
    return segments


def get_top_keywords(texts: list[str], n: int = 8) -> list[str]:
    """Extract top N TF-IDF keywords from a list of texts."""
    if not texts:
        return []
    try:
        vec = TfidfVectorizer(stop_words='english', max_features=500, ngram_range=(1, 2))
        matrix = vec.fit_transform(texts)
        scores = np.asarray(matrix.sum(axis=0)).flatten()
        indices = scores.argsort()[-n:][::-1]
        feature_names = vec.get_feature_names_out()
        return [feature_names[i] for i in indices]
    except Exception:
        return []

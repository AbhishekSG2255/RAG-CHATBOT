"""
retriever.py — Hybrid retrieval: semantic (FAISS) + keyword (TF-IDF BM25-like).

Query handling:
  1. Embed the query with sentence-transformers.
  2. Search FAISS for top-k nearest message chunks (semantic).
  3. Score topic summaries using TF-IDF keyword match.
  4. Combine results and generate an answer from context.
  5. Optionally use Groq API for better natural language answers.
"""

import json
import logging
import re
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

TOP_K_SEMANTIC = 5
TOP_K_TOPIC = 3


def retrieve_and_answer(
    query: str,
    faiss_index,
    chunk_meta: list,
    topic_summaries: list[dict],
    hundred_summaries: list[dict],
    messages_db,
    groq_api_key: str = '',
) -> dict:
    """
    Main retrieval + answer generation function.

    Returns:
        {
            'answer': str,
            'sources': {
                'semantic_chunks': list,
                'topic_summaries': list,
            }
        }
    """
    from .embedder import embed_query

    # 1. Semantic search
    query_vec = embed_query(query)
    semantic_chunks = _semantic_search(query_vec, faiss_index, chunk_meta, TOP_K_SEMANTIC)

    # 2. Topic summary keyword search
    matched_topics = _keyword_search_topics(query, topic_summaries, TOP_K_TOPIC)

    # 3. Build context
    context = _build_context(query, semantic_chunks, matched_topics, hundred_summaries)

    # 4. Generate answer
    if groq_api_key:
        answer = _groq_answer(query, context, groq_api_key)
    else:
        answer = _extractive_answer(query, context)

    return {
        'answer': answer,
        'sources': {
            'semantic_chunks': semantic_chunks[:3],
            'topic_summaries': matched_topics,
        }
    }


def _semantic_search(query_vec: np.ndarray, index, chunk_meta: list, k: int) -> list:
    """Search FAISS index for nearest chunks."""
    if index is None or not chunk_meta:
        return []
    try:
        distances, indices = index.search(query_vec, k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(chunk_meta):
                chunk = dict(chunk_meta[idx])
                chunk['score'] = float(1 / (1 + dist))  # Convert distance to similarity
                results.append(chunk)
        return results
    except Exception as e:
        logger.error(f"FAISS search error: {e}")
        return []


def _keyword_search_topics(query: str, topic_summaries: list[dict], k: int) -> list:
    """Find most relevant topic summaries using TF-IDF cosine similarity."""
    if not topic_summaries:
        return []

    texts = [t.get('summary', '') for t in topic_summaries]
    texts_with_query = texts + [query]

    try:
        vec = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        matrix = vec.fit_transform(texts_with_query)
        query_vec = matrix[-1]
        topic_matrix = matrix[:-1]
        scores = cosine_similarity(query_vec, topic_matrix)[0]
        top_indices = np.argsort(scores)[-k:][::-1]
        results = []
        for i in top_indices:
            if scores[i] > 0.01:
                topic = dict(topic_summaries[i])
                topic['score'] = float(scores[i])
                results.append(topic)
        return results
    except Exception as e:
        logger.warning(f"Keyword search error: {e}")
        return []


def _build_context(query: str, chunks: list, topics: list, hundreds: list) -> str:
    """Assemble context string from retrieved sources."""
    parts = []

    if topics:
        parts.append("=== Relevant Topic Summaries ===")
        for t in topics:
            parts.append(f"Topic {t.get('topic_number', '?')} (messages {t.get('start_global_index', '?')}–{t.get('end_global_index', '?')}):")
            parts.append(t.get('summary', ''))
            kw = t.get('keywords', [])
            if isinstance(kw, str):
                try:
                    kw = json.loads(kw)
                except Exception:
                    kw = []
            if kw:
                parts.append(f"Keywords: {', '.join(kw)}")
            parts.append("")

    if chunks:
        parts.append("=== Relevant Conversation Excerpts ===")
        for c in chunks:
            parts.append(f"[Messages {c.get('start_global', '?')}–{c.get('end_global', '?')}]:")
            parts.append(c.get('preview', ''))
            parts.append("")

    return '\n'.join(parts)


def _extractive_answer(query: str, context: str) -> str:
    """
    Generate an answer by extracting the most relevant sentences from context.
    This is a simple but effective approach without any external API.
    """
    if not context.strip():
        return "I don't have enough context to answer that question based on the conversations."

    query_lower = query.lower()

    # Detect question type
    if any(w in query_lower for w in ['habit', 'routine', 'daily', 'sleep', 'eat', 'food', 'exercise']):
        answer_type = 'habits'
    elif any(w in query_lower for w in ['person', 'who', 'kind', 'type', 'personality', 'character']):
        answer_type = 'personality'
    elif any(w in query_lower for w in ['talk', 'speak', 'communicate', 'style', 'write', 'message']):
        answer_type = 'communication'
    elif any(w in query_lower for w in ['job', 'work', 'occupation', 'career', 'profession']):
        answer_type = 'work'
    elif any(w in query_lower for w in ['hobby', 'fun', 'interest', 'like', 'enjoy', 'leisure']):
        answer_type = 'hobbies'
    elif any(w in query_lower for w in ['family', 'friend', 'relationship', 'pet', 'dog', 'cat']):
        answer_type = 'relationships'
    else:
        answer_type = 'general'

    # Split context into sentences and score them
    sentences = re.split(r'(?<=[.!?])\s+', context)
    sentences = [s.strip() for s in sentences
                 if len(s.strip()) > 20 and not s.startswith('===') and not s.startswith('[')]

    if not sentences:
        return "Based on the conversations, I found some relevant context but couldn't extract a specific answer. " \
               "Please try rephrasing your question."

    # Score sentences by relevance to query words
    query_words = set(re.sub(r'[^\w\s]', '', query_lower).split())
    scored = []
    for s in sentences:
        s_lower = s.lower()
        score = sum(1 for w in query_words if w in s_lower)
        scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    top_sentences = [s for _, s in scored[:4] if _]

    if not top_sentences:
        top_sentences = sentences[:3]

    # Build a coherent response
    intro_map = {
        'habits': "Based on the conversations, here are the user's habits and routines:",
        'personality': "Based on the conversations, here's what we know about this person:",
        'communication': "Based on the conversations, here's how this user communicates:",
        'work': "Based on the conversations, here's what we know about their work:",
        'hobbies': "Based on the conversations, here are their interests and hobbies:",
        'relationships': "Based on the conversations, here's what we know about their relationships:",
        'general': "Based on the conversations, here's what I found:",
    }

    intro = intro_map.get(answer_type, intro_map['general'])
    answer_body = ' '.join(top_sentences)
    return f"{intro}\n\n{answer_body}"


def _groq_answer(query: str, context: str, api_key: str) -> str:
    """Use Groq API (Llama 3) for high-quality natural language answers."""
    import requests

    prompt = f"""You are a helpful assistant analyzing conversation data. 
Use ONLY the provided context to answer the question. Be concise and specific.

Context from conversations:
{context[:3000]}

Question: {query}

Answer:"""

    try:
        resp = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'llama3-8b-8192',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 500,
                'temperature': 0.3,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.warning(f"Groq API error: {e}, falling back to extractive")
        return _extractive_answer(query, context)

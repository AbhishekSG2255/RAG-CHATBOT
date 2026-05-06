"""
preprocessor.py — Parse conversations.csv into structured messages.

Each row in the CSV is one day's conversation containing lines like:
  "User 1: Hello there!
   User 2: Hi! How are you?
   User 1: I'm doing well."

We parse every row into individual Message objects and assign a
monotonically increasing global_index across ALL conversations.
"""

import re
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Pattern to split on speaker turns, e.g. "User 1: " or "User 2: "
SPEAKER_PATTERN = re.compile(r'(User \d+)\s*:\s*')


def parse_csv(csv_path: str) -> list[dict]:
    """
    Read the CSV and return a flat list of message dicts.

    Returns:
        list of {
            'conversation_id': int,   # row index in CSV (= day)
            'global_index': int,      # position across ALL messages
            'speaker': str,           # 'User 1' or 'User 2'
            'text': str,              # the message text
        }
    """
    logger.info(f"Reading CSV from {csv_path}")

    # The CSV has no header, each row is a raw multi-line conversation string
    df = pd.read_csv(csv_path, header=None, names=['conversation'], dtype=str)
    df = df.dropna(subset=['conversation'])

    messages = []
    global_index = 0

    for conv_id, row in enumerate(df['conversation']):
        conv_messages = _parse_conversation(row, conv_id, global_index)
        messages.extend(conv_messages)
        global_index += len(conv_messages)

        if conv_id % 1000 == 0:
            logger.info(f"  Parsed {conv_id}/{len(df)} conversations, {global_index} messages so far")

    logger.info(f"Total messages parsed: {global_index}")
    return messages


def _parse_conversation(raw_text: str, conv_id: int, start_index: int) -> list[dict]:
    """Parse a single conversation string into message dicts."""
    raw_text = str(raw_text).strip().strip('"').strip()
    if not raw_text:
        return []

    # Split by speaker turns
    parts = SPEAKER_PATTERN.split(raw_text)
    # parts = ['', 'User 1', 'Hello there!\n', 'User 2', 'Hi!', ...]
    # Skip first empty string if present
    messages = []
    i = 1  # start after the leading empty ''
    local_index = 0

    while i < len(parts) - 1:
        speaker = parts[i].strip()
        text = parts[i + 1].strip()
        text = text.replace('\n', ' ').replace('\r', ' ').strip()
        if text and speaker.startswith('User'):
            messages.append({
                'conversation_id': conv_id,
                'global_index': start_index + local_index,
                'speaker': speaker,
                'text': text,
            })
            local_index += 1
        i += 2

    return messages

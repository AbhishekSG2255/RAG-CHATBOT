"""
extractor.py — Rule-based persona extraction from conversation messages.

No external LLM needed. Uses pattern matching, keyword lists, and
statistical analysis of message text to infer:
  - Habits (food, sleep, exercise, routines)
  - Personal facts (occupation, family, location, pets)
  - Personality traits (humor, empathy, positivity, etc.)
  - Communication style (message length, emoji use, formality, tone)
"""

import re
import json
import logging
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# ─── Keyword Dictionaries ──────────────────────────────────────────────────────

OCCUPATION_KEYWORDS = {
    'software engineer': ['software engineer', 'programmer', 'developer', 'coding', 'code'],
    'teacher': ['teacher', 'teaching', 'students', 'classroom', 'school', 'kindergarten', 'grade'],
    'nurse': ['nurse', 'nursing', 'patients', 'hospital', 'medical'],
    'doctor': ['doctor', 'physician', 'medicine', 'medical school', 'residency', 'med student'],
    'chef': ['chef', 'cook', 'restaurant', 'culinary', 'kitchen', 'bake'],
    'musician': ['musician', 'guitar', 'piano', 'band', 'music', 'singing', 'singer', 'choir'],
    'artist': ['artist', 'muralist', 'painter', 'artwork', 'creative'],
    'firefighter': ['firefighter', 'fire station', 'rescue'],
    'police officer': ['police', 'officer', 'trooper', 'law enforcement'],
    'writer': ['writer', 'author', 'blog', 'novelist', 'journalist'],
    'photographer': ['photographer', 'photography', 'photos', 'photoshoot'],
    'personal trainer': ['personal trainer', 'fitness', 'gym', 'workout'],
    'park ranger': ['park ranger', 'ranger', 'national park'],
    'actor': ['actress', 'actor', 'acting', 'performance', 'audition'],
    'student': ['student', 'studying', 'college', 'university', 'graduate'],
    'EMT': ['emt', 'paramedic', 'emergency medical'],
    'dentist': ['dentist', 'dental', 'teeth'],
}

HOBBY_KEYWORDS = {
    'hiking': ['hike', 'hiking', 'trail', 'backpacking', 'outdoors'],
    'cooking': ['cook', 'cooking', 'recipe', 'bake', 'baking', 'kitchen', 'meal'],
    'reading': ['read', 'reading', 'book', 'novel', 'author', 'library'],
    'gaming': ['video game', 'gaming', 'skyrim', 'fallout', 'playstation', 'xbox'],
    'fishing': ['fish', 'fishing', 'angling', 'catch'],
    'running': ['run', 'running', 'jog', 'marathon', 'sprint'],
    'dancing': ['dance', 'dancing', 'salsa', 'ballet'],
    'photography': ['photograph', 'camera', 'photo', 'shoot'],
    'gardening': ['garden', 'gardening', 'plant', 'flower', 'vegetable'],
    'music': ['guitar', 'piano', 'sing', 'song', 'band', 'concert', 'karaoke'],
    'travel': ['travel', 'trip', 'vacation', 'visit', 'journey', 'flew'],
    'yoga': ['yoga', 'meditation', 'mindfulness'],
    'camping': ['camp', 'camping', 'tent', 'bonfire'],
    'writing': ['write', 'writing', 'journal', 'story', 'poem'],
    'watching movies': ['movie', 'film', 'netflix', 'cinema', 'watch'],
    'sports': ['soccer', 'football', 'basketball', 'baseball', 'sport'],
    'archery': ['archery', 'bow', 'arrow'],
    'scuba diving': ['scuba', 'diving', 'snorkel'],
    'cycling': ['bike', 'cycling', 'bicycle', 'ride'],
    'video games': ['video game', 'gamer', 'gaming', 'playstation'],
}

FOOD_KEYWORDS = ['pizza', 'tacos', 'chicken', 'pasta', 'sushi', 'burger', 'salad',
                 'vegetarian', 'vegan', 'spicy', 'dessert', 'cake', 'coffee', 'tea',
                 'lasagna', 'enchiladas', 'mexican', 'italian', 'chinese', 'indian',
                 'hummus', 'chocolate', 'cookie', 'soup', 'sandwich']

PET_KEYWORDS = {
    'dog': ['dog', 'puppy', 'canine', 'labrador', 'retriever', 'shepherd', 'poodle', 'hound'],
    'cat': ['cat', 'kitten', 'feline', 'tabby', 'kitty'],
    'horse': ['horse', 'pony', 'equine', 'mare', 'stallion'],
    'bird': ['bird', 'parrot', 'parakeet', 'canary', 'cockatiel'],
    'fish': ['fish', 'aquarium', 'goldfish'],
}

FAMILY_KEYWORDS = {
    'has kids': ['my kid', 'my son', 'my daughter', 'my children', 'as a parent', 'my baby',
                 'my boys', 'my girls'],
    'has siblings': ['my brother', 'my sister', 'my sibling'],
    'married/partner': ['my husband', 'my wife', 'my partner', 'my spouse', 'my girlfriend', 'my boyfriend'],
    'close to family': ['my family', 'my parents', 'my mom', 'my dad', 'my mother', 'my father'],
}

POSITIVE_WORDS = ['love', 'great', 'awesome', 'amazing', 'wonderful', 'fantastic', 'excellent',
                   'happy', 'excited', 'enjoy', 'fun', 'glad', 'lucky', 'blessed']
NEGATIVE_WORDS = ['sad', 'upset', 'angry', 'frustrated', 'worried', 'scared', 'nervous',
                   'difficult', 'hard', 'struggle', 'miss', 'lonely']
HUMOR_PATTERNS = ['lol', 'haha', 'hehe', '😂', '😄', '😁', 'funny', 'hilarious', 'joke']
EMPATHY_PATTERNS = ["i'm sorry", "that's tough", "i understand", "i can imagine",
                     "must be hard", "feel better", "hope you"]


# ─── Main Extractor ────────────────────────────────────────────────────────────

def _extract_persona_for_speaker(messages: list[dict], speaker: str) -> dict:
    speaker_messages = [m for m in messages if m.get('speaker') == speaker]
    if not speaker_messages:
        return {}
        
    all_texts = [m['text'] for m in speaker_messages]
    combined_lower = ' '.join(all_texts).lower()

    habits = _extract_habits(all_texts, combined_lower)
    personal_facts = _extract_personal_facts(all_texts, combined_lower)
    personality = _extract_personality(all_texts, combined_lower)
    comm_style = _extract_communication_style(all_texts)
    summary = _build_summary(habits, personal_facts, personality, comm_style)

    return {
        "habits": habits,
        "personal_facts": personal_facts,
        "personality": personality,
        "communication_style": comm_style,
        "summary": summary,
        "total_messages_analyzed": len(speaker_messages),
    }


def extract_persona(messages: list[dict]) -> dict:
    """
    Extract a structured persona from message dicts, separated by speaker.

    Returns a dict suitable for JSON serialization:
    {
        "User 1": { "habits": [...], ... },
        "User 2": { "habits": [...], ... }
    }
    """
    logger.info(f"Extracting persona from {len(messages)} messages...")

    persona = {
        "User 1": _extract_persona_for_speaker(messages, "User 1"),
        "User 2": _extract_persona_for_speaker(messages, "User 2"),
    }

    logger.info("Persona extraction complete.")
    return persona


def _extract_habits(texts: list[str], combined_lower: str) -> list[str]:
    habits = []

    # Food habits
    found_foods = [f for f in FOOD_KEYWORDS if f in combined_lower]
    if found_foods:
        top_foods = Counter(found_foods).most_common(4)
        habits.append(f"Mentions food/drinks frequently: {', '.join([f[0] for f in top_foods])}")

    # Exercise
    exercise_words = ['run', 'running', 'gym', 'workout', 'exercise', 'yoga', 'hike', 'hiking',
                       'walk', 'walking', 'swim', 'swimming', 'cycle', 'cycling', 'fitness']
    exercise_found = [w for w in exercise_words if w in combined_lower]
    if len(exercise_found) >= 2:
        habits.append("Physically active — mentions exercise, hiking, or outdoor activity regularly")

    # Outdoor activities
    if any(w in combined_lower for w in ['outdoors', 'nature', 'park', 'trail', 'hike']):
        habits.append("Enjoys spending time outdoors and in nature")

    # Reading habit
    read_count = combined_lower.count('read') + combined_lower.count('book') + combined_lower.count('novel')
    if read_count >= 5:
        habits.append("Avid reader — frequently mentions books and reading")

    # Cooking
    cook_count = combined_lower.count('cook') + combined_lower.count('recipe') + combined_lower.count('bake')
    if cook_count >= 3:
        habits.append("Enjoys cooking and trying new recipes at home")

    # Music
    music_count = sum(combined_lower.count(w) for w in ['music', 'guitar', 'piano', 'sing', 'song'])
    if music_count >= 3:
        habits.append("Music is a significant part of their life — listens and/or plays instruments")

    # Family time
    family_count = sum(combined_lower.count(w) for w in ['family', 'kids', 'children', 'daughter', 'son'])
    if family_count >= 5:
        habits.append("Prioritizes spending quality time with family")

    # Pet care
    pets_found = [pet for pet, kws in PET_KEYWORDS.items()
                  if any(kw in combined_lower for kw in kws)]
    if pets_found:
        habits.append(f"Pet owner — has {', '.join(set(pets_found))}")

    return habits if habits else ["No strong habitual patterns detected in conversations"]


def _extract_personal_facts(texts: list[str], combined_lower: str) -> dict:
    facts = {}

    # Occupations
    found_occupations = []
    for occ, keywords in OCCUPATION_KEYWORDS.items():
        if any(kw in combined_lower for kw in keywords):
            found_occupations.append(occ)
    if found_occupations:
        facts['likely_occupations'] = list(set(found_occupations))

    # Hobbies
    found_hobbies = []
    for hobby, keywords in HOBBY_KEYWORDS.items():
        count = sum(combined_lower.count(kw) for kw in keywords)
        if count >= 2:
            found_hobbies.append(hobby)
    if found_hobbies:
        facts['hobbies'] = list(set(found_hobbies))[:10]

    # Pets
    found_pets = [pet for pet, kws in PET_KEYWORDS.items()
                  if any(kw in combined_lower for kw in kws)]
    if found_pets:
        facts['pets'] = list(set(found_pets))

    # Family relationships
    family_facts = []
    for rel, keywords in FAMILY_KEYWORDS.items():
        if any(kw in combined_lower for kw in keywords):
            family_facts.append(rel)
    if family_facts:
        facts['family_relationships'] = family_facts

    # Location mentions
    locations = _extract_locations(combined_lower)
    if locations:
        facts['mentioned_locations'] = locations[:8]

    # Books/Authors
    book_mentions = _extract_books(combined_lower)
    if book_mentions:
        facts['mentioned_books_authors'] = book_mentions[:6]

    return facts


def _extract_personality(texts: list[str], combined_lower: str) -> dict:
    personality = {}

    # Positivity score
    pos_count = sum(combined_lower.count(w) for w in POSITIVE_WORDS)
    neg_count = sum(combined_lower.count(w) for w in NEGATIVE_WORDS)
    total = pos_count + neg_count
    if total > 0:
        pos_ratio = pos_count / total
        if pos_ratio > 0.7:
            personality['overall_tone'] = 'very positive and upbeat'
        elif pos_ratio > 0.5:
            personality['overall_tone'] = 'generally positive'
        else:
            personality['overall_tone'] = 'balanced / realistic'

    # Humor
    humor_count = sum(combined_lower.count(h) for h in HUMOR_PATTERNS)
    if humor_count >= 3:
        personality['humor'] = 'frequently uses humor and lighthearted expressions'
    elif humor_count >= 1:
        personality['humor'] = 'occasionally uses humor'

    # Empathy
    empathy_count = sum(combined_lower.count(e) for e in EMPATHY_PATTERNS)
    if empathy_count >= 3:
        personality['empathy'] = 'highly empathetic — often acknowledges others feelings'
    elif empathy_count >= 1:
        personality['empathy'] = 'shows empathy when appropriate'

    # Curiosity
    question_marks = combined_lower.count('?')
    if question_marks >= 50:
        personality['curiosity'] = 'very curious — asks many questions'
    elif question_marks >= 20:
        personality['curiosity'] = 'moderately curious'

    # Openness
    sharing_words = ['i love', "i'm a", 'i enjoy', 'i like', 'my favorite', 'i feel', 'i think']
    sharing_count = sum(combined_lower.count(w) for w in sharing_words)
    if sharing_count >= 20:
        personality['openness'] = 'very open and willing to share personal details'
    elif sharing_count >= 10:
        personality['openness'] = 'moderately open'

    # Excitement
    exclamation_pct = combined_lower.count('!') / max(len(texts), 1)
    if exclamation_pct > 1.5:
        personality['enthusiasm'] = 'highly enthusiastic — uses many exclamation marks'
    elif exclamation_pct > 0.5:
        personality['enthusiasm'] = 'generally enthusiastic'

    # Key traits summary
    traits = []
    if personality.get('overall_tone', '').startswith('very positive'):
        traits.append('optimistic')
    if 'highly empathetic' in personality.get('empathy', ''):
        traits.append('empathetic')
    if 'frequently' in personality.get('humor', ''):
        traits.append('humorous')
    if 'very curious' in personality.get('curiosity', ''):
        traits.append('curious')
    if 'very open' in personality.get('openness', ''):
        traits.append('open')
    if traits:
        personality['key_traits'] = traits

    return personality


def _extract_communication_style(texts: list[str]) -> dict:
    style = {}

    if not texts:
        return style

    lengths = [len(t.split()) for t in texts]
    avg_len = sum(lengths) / len(lengths)
    style['avg_words_per_message'] = round(avg_len, 1)

    if avg_len < 8:
        style['message_length'] = 'very short (concise, quick replies)'
    elif avg_len < 20:
        style['message_length'] = 'short to medium (conversational)'
    elif avg_len < 40:
        style['message_length'] = 'medium (detailed responses)'
    else:
        style['message_length'] = 'long (very detailed, elaborate responses)'

    combined = ' '.join(texts).lower()

    # Exclamation usage
    excl_count = combined.count('!')
    style['exclamation_usage'] = 'frequent' if excl_count > len(texts) * 0.5 else 'occasional'

    # Question style
    q_count = combined.count('?')
    style['question_asking'] = 'frequent' if q_count > len(texts) * 0.3 else 'occasional'

    # Formality
    formal_words = ['certainly', 'indeed', 'however', 'therefore', 'nevertheless', 'furthermore']
    informal_words = ['gonna', 'wanna', 'gotta', 'yeah', 'yep', 'nope', 'lol', 'omg', 'btw']
    formal_count = sum(combined.count(w) for w in formal_words)
    informal_count = sum(combined.count(w) for w in informal_words)

    if informal_count > formal_count * 2:
        style['formality'] = 'very casual and informal'
    elif informal_count > formal_count:
        style['formality'] = 'casual'
    elif formal_count > informal_count:
        style['formality'] = 'moderately formal'
    else:
        style['formality'] = 'neutral'

    # Emoji usage
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0\U000024C2-\U0001F251]+",
        flags=re.UNICODE
    )
    emoji_count = len(emoji_pattern.findall(combined))
    style['emoji_usage'] = 'frequent' if emoji_count > 10 else ('occasional' if emoji_count > 0 else 'rare')

    # Signature phrases (most common 3-grams)
    words = combined.split()
    if len(words) >= 3:
        trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        common_trigrams = Counter(trigrams).most_common(5)
        style['common_phrases'] = [tg for tg, cnt in common_trigrams if cnt >= 3]

    return style


def _extract_locations(text: str) -> list[str]:
    """Extract likely location mentions."""
    location_patterns = [
        r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
        r'\bfrom\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
        r'\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
    ]
    locations = set()
    # Use original-case text
    for pattern in location_patterns:
        matches = re.findall(pattern, text.title())
        locations.update(matches)
    # Filter out common non-places
    exclude = {'The', 'My', 'Your', 'Our', 'Her', 'His', 'Their', 'Me', 'You',
               'We', 'It', 'This', 'That', 'A', 'An', 'And', 'Or', 'But'}
    return [loc for loc in locations if loc not in exclude and len(loc) > 2][:8]


def _extract_books(text: str) -> list[str]:
    """Extract book/author mentions."""
    known = [
        'harry potter', 'outlander', 'the nightingale', 'the great gatsby',
        'the princess bride', 'name of the wind', 'stephen king', 'jane austen',
        'ken follett', 'diana gabaldon', 'charles dickens', 'kristin hannah',
        'patrick rothfuss', 'dean koontz'
    ]
    return [b.title() for b in known if b in text]


def _build_summary(habits, personal_facts, personality, comm_style) -> str:
    """Build a one-paragraph human-readable persona summary."""
    parts = []

    occ = personal_facts.get('likely_occupations', [])
    if occ:
        parts.append(f"This user appears to be or mentions occupations like: {', '.join(occ[:3])}.")

    tone = personality.get('overall_tone', '')
    if tone:
        parts.append(f"They tend to be {tone} in their conversations.")

    key_traits = personality.get('key_traits', [])
    if key_traits:
        parts.append(f"Key personality traits: {', '.join(key_traits)}.")

    hobbies = personal_facts.get('hobbies', [])
    if hobbies:
        parts.append(f"Their interests include: {', '.join(hobbies[:5])}.")

    msg_len = comm_style.get('message_length', '')
    formality = comm_style.get('formality', '')
    if msg_len or formality:
        parts.append(f"Communication style: {msg_len}, {formality}.")

    return ' '.join(parts) if parts else "Persona data is being built from conversations."

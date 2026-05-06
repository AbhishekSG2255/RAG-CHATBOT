"""
store.py — Persona JSON persistence layer.
Saves and loads persona data from Django model + disk JSON file.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)


def save_persona(persona_dict: dict, json_path: str):
    """Save persona dict to JSON file."""
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(persona_dict, f, indent=2, ensure_ascii=False)
    logger.info(f"Persona saved to {json_path}")


def load_persona(json_path: str) -> dict:
    """Load persona dict from JSON file."""
    if not os.path.exists(json_path):
        return {}
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_persona_to_db(persona_dict: dict):
    """Save/update persona in Django database."""
    from api.models import Persona
    obj, _ = Persona.objects.get_or_create(pk=1)
    obj.data = json.dumps(persona_dict)
    obj.save()
    logger.info("Persona saved to database.")


def load_persona_from_db() -> dict:
    """Load persona from Django database."""
    from api.models import Persona
    try:
        obj = Persona.objects.get(pk=1)
        return obj.get_data()
    except Persona.DoesNotExist:
        return {}

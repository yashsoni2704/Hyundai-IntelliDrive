"""
Session context: track vehicle/topic and resolve vague follow-up queries.

This module is the "brain" for understanding what the user means:
  - normalize_message: fix typos (milage → mileage, tucsan → tucson)
  - detect_vehicle / detect_topic: parse intent from text
  - resolve_query: expand "its mileage" → "What is the mileage of Hyundai Creta?"
  - needs_clarification: ask for car model when context is missing
  - update_context: remember last car/topic after each exchange

Context is stored as JSON in chat_sessions.context_json (see session_service.py).
"""

from __future__ import annotations

import json
import re
from difflib import get_close_matches
from typing import Any

VEHICLE_MODELS = [
    "creta",
    "venue",
    "i20",
    "verna",
    "alcazar",
    "tucson",
    "ioniq",
    "kona",
    "aura",
    "exter",
    "grand i10",
    "nios",
]

VEHICLE_ALIASES: dict[str, str] = {
    "ioniq 5": "ioniq",
    "ioniq5": "ioniq",
    "kona electric": "kona",
    "grand i10 nios": "nios",
    "i 20": "i20",
    "i-20": "i20",
}

NOT_OUR_CAR_MESSAGE = (
    "Sorry, that is not a Hyundai model in our knowledge base. "
    "Please ask about Hyundai cars such as Creta, Venue, Verna, or Tucson."
)

TOPIC_QUERY_TERMS = {
    "price",
    "cost",
    "lakh",
    "rupee",
    "mileage",
    "milage",
    "kmpl",
    "fuel",
    "seat",
    "seater",
    "seating",
    "compare",
    "comparison",
    "versus",
    "feature",
    "features",
    "spec",
    "specs",
    "book",
    "booking",
    "warranty",
    "service",
    "schedule",
    "test",
    "drive",
}

GENERIC_AUTO_TERMS = {
    "suv",
    "sedan",
    "hatchback",
    "vehicle",
    "vehicles",
    "ev",
    "electric",
    "petrol",
    "diesel",
    "variant",
    "variants",
    "model",
    "models",
    "new",
    "latest",
    "best",
    "family",
    "highway",
    "city",
    "compact",
    "premium",
    "luxury",
    "affordable",
    "vs",
    "and",
    "or",
    "my",
    "your",
}

QUERY_STOPWORDS = {
    "a",
    "an",
    "about",
    "are",
    "can",
    "car",
    "cars",
    "does",
    "give",
    "hyundai",
    "i",
    "in",
    "is",
    "know",
    "me",
    "of",
    "please",
    "show",
    "tell",
    "the",
    "to",
    "want",
    "what",
    "when",
    "which",
    "how",
    "many",
    "much",
    "this",
    "that",
    "with",
    "it",
    "its",
}


def build_known_hyundai_terms() -> frozenset[str]:
    """Lowercase tokens for every Hyundai model in our FAQ database."""
    terms: set[str] = set()
    for model in VEHICLE_MODELS:
        terms.add(model.lower())
        for part in model.split():
            terms.add(part)
    for alias, canonical in VEHICLE_ALIASES.items():
        terms.add(alias.lower())
        terms.add(canonical.lower())
        for part in alias.split():
            terms.add(part)
    return frozenset(terms)


_KNOWN_HYUNDAI_TERMS: frozenset[str] | None = None


def get_known_hyundai_terms() -> frozenset[str]:
    global _KNOWN_HYUNDAI_TERMS
    if _KNOWN_HYUNDAI_TERMS is None:
        _KNOWN_HYUNDAI_TERMS = build_known_hyundai_terms()
    return _KNOWN_HYUNDAI_TERMS


def is_our_hyundai_model(term: str) -> bool:
    """True when a token matches a Hyundai model in our database."""
    token = term.lower()
    known = get_known_hyundai_terms()
    if token in known:
        return True
    for model_token in known:
        if len(token) >= 3 and (token in model_token or model_token in token):
            return True
    return False


def query_entity_terms(query: str) -> set[str]:
    """Model-like tokens in a query (excludes topics and generic car words)."""
    normalized = normalize_message(query)
    tokens = {
        term
        for term in re.findall(r"[a-z0-9]+", normalized.lower())
        if term not in QUERY_STOPWORDS
    }
    return {
        term
        for term in tokens
        if term not in TOPIC_QUERY_TERMS and term not in GENERIC_AUTO_TERMS
    }


def mentions_unknown_vehicle(query: str) -> bool:
    """
    True when the user names a car that is not in our Hyundai model list.
    Generic questions (e.g. 'what is the price') return False — clarification handles those.
    """
    entity_terms = query_entity_terms(query)
    if not entity_terms:
        return False
    return any(not is_our_hyundai_model(term) for term in entity_terms)


def is_low_signal_query(query: str) -> bool:
    """Gibberish, single-letter, or meta text — must not reuse session context."""
    stripped = normalize_message(query).strip().lower()
    if len(stripped) < 2:
        return True
    if stripped in {
        "a",
        "no",
        "ok",
        "yes",
        "hi",
        "hello",
        "test",
        "why",
        "hmm",
        "help",
    }:
        return True
    if re.fullmatch(r"(no\s+)?data(\s+not)?\s+found", stripped):
        return True
    entity_terms = query_entity_terms(query)
    if entity_terms:
        return False
    if detect_vehicle(query) or detect_topic(query):
        return False
    words = [
        w
        for w in re.findall(r"[a-z0-9]+", stripped)
        if w not in QUERY_STOPWORDS and w not in TOPIC_QUERY_TERMS
    ]
    return len(words) <= 2

SPELLING_FIXES: dict[str, str] = {
    "alcazr": "alcazar",
    "alacazar": "alcazar",
    "alazar": "alcazar",
    "alcazar": "alcazar",
    "tucsan": "tucson",
    "tuscon": "tucson",
    "tuscan": "tucson",
    "cret": "creta",
    "creeta": "creta",
    "kreta": "creta",
    "vernaa": "verna",
    "verana": "verna",
    "milege": "mileage",
    "milage": "mileage",
    "milaege": "mileage",
    "milage": "mileage",
    "priice": "price",
    "pric": "price",
    "venu": "venue",
    "vunue": "venue",
    "extar": "exter",
    "exter": "exter",
    "i20": "i20",
    "compair": "compare",
    "compar": "compare",
    "comare": "compare",
    "detials": "details",
    "deatils": "details",
}

CLARIFICATION_MESSAGE = (
    "Please clarify your question. For example, you can ask:\n"
    "• What is the price of Hyundai {vehicle}?\n"
    "• What is the mileage of Hyundai {vehicle}?\n"
    "• Tell me about Hyundai {vehicle}"
)

GENERIC_CLARIFICATION = (
    "Please clarify your question. For example, you can ask:\n"
    "• What is the price of Hyundai Creta?\n"
    "• What is the mileage of Hyundai Venue?\n"
    "• Compare Hyundai Creta and Verna"
)

VEHICLE_MODEL_PROMPT = (
    "Which Hyundai car model are you asking about?\n"
    "Please reply with a model name (e.g. Creta, Venue, Alcazar, Verna, Tucson, i20).\n"
    "{topic_hint}"
)

TOPIC_HINTS = {
    "price": "I'll then share its price details.",
    "mileage": "I'll then share its mileage details.",
    "seats": "I'll then share its seating capacity.",
    "features": "I'll then share its features.",
    "compare": "I'll then compare it with another model.",
    "booking": "I'll then help you book a test drive.",
    "service": "I'll then share service and warranty details.",
}

VAGUE_PHRASES = [
    "my car",
    "that car",
    "this car",
    "the car",
    "it",
    "its",
    "it's",
    "same car",
    "that one",
    "this one",
    "about my",
    "tell me more",
    "more details",
    "what about it",
    "i want to know",
]


def default_context() -> dict[str, Any]:
    return {
        "last_vehicle": "",
        "last_topic": "",
        "pending_topic": "",
        "pending_vehicle": "",
        "recent_queries": [],
    }


def coerce_context(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Merge a client-supplied context dict with defaults (guest chat round-trip)."""
    if not raw:
        return default_context()
    base = default_context()
    base.update({k: v for k, v in raw.items() if k in base})
    return base


def parse_context(raw: str | None) -> dict[str, Any]:
    if not raw:
        return default_context()
    try:
        data = json.loads(raw)
        base = default_context()
        base.update({k: v for k, v in data.items() if k in base})
        return base
    except (json.JSONDecodeError, TypeError):
        return default_context()


def serialize_context(ctx: dict[str, Any]) -> str:
    return json.dumps(ctx)


def normalize_message(text: str) -> str:
    """Fix common typos and normalize vehicle aliases before search."""
    lower = text.lower().strip()
    for alias, canonical in sorted(VEHICLE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        lower = lower.replace(alias, canonical)
    tokens = re.findall(r"[a-z0-9]+", lower)
    fixed_tokens: list[str] = []
    for token in tokens:
        if token in SPELLING_FIXES:
            fixed_tokens.append(SPELLING_FIXES[token])
            continue
        match = get_close_matches(token, VEHICLE_MODELS, n=1, cutoff=0.82)
        if match and len(token) >= 4:
            fixed_tokens.append(match[0])
        else:
            fixed_tokens.append(token)
    if not fixed_tokens:
        return text.strip()
  # Preserve original casing loosely by rebuilding from fixed tokens
    return " ".join(fixed_tokens)


def detect_vehicle(text: str) -> str:
    lower = normalize_message(text).lower()
    for alias, canonical in sorted(VEHICLE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in lower:
            return _display_name(canonical)
    for model in sorted(VEHICLE_MODELS, key=len, reverse=True):
        if model in lower:
            return _display_name(model)
    return ""


def _display_name(model: str) -> str:
    if model == "grand i10":
        return "Grand I10"
    if model == "nios":
        return "Nios"
    if model == "ioniq":
        return "Ioniq"
    return model.title()


def _is_vehicle_only_query(message: str) -> bool:
    normalized = normalize_message(message)
    vehicle = detect_vehicle(normalized)
    if not vehicle:
        return False
    topic = detect_topic(normalized)
    if topic:
        return False
    words = [
        w
        for w in re.findall(r"[a-z0-9]+", normalized.lower())
        if w not in ("hyundai", "car", "cars", "about", "tell", "me")
    ]
    return len(words) <= 2


def needs_clarification(message: str, ctx: dict[str, Any] | None = None) -> bool:
    """Return True when the user query is too vague to answer accurately."""
    ctx = ctx or {}
    normalized = normalize_message(message)
    lower = normalized.lower().strip()
    topic = detect_topic(normalized)
    vehicle = detect_vehicle(normalized)
    last_vehicle = ctx.get("last_vehicle") or ""
    pending_topic = ctx.get("pending_topic") or ""

    if pending_topic and vehicle:
        return False
    if ctx.get("pending_vehicle") and topic:
        return False

    if vehicle and topic:
        return False

    if _is_vehicle_only_query(normalized) and not pending_topic:
        return True

    if is_vague_query(normalized) and not last_vehicle:
        return True

    if topic and not vehicle and not last_vehicle:
        return True

    words = [w for w in re.findall(r"[a-z0-9]+", lower) if w not in ("hyundai", "car", "cars")]
    if not vehicle and not last_vehicle and not topic:
        if len(words) <= 1:
            return True

    vague_words = {
        "details",
        "detail",
        "info",
        "information",
        "about",
        "specs",
        "spec",
        "specification",
        "specifications",
        "something",
        "anything",
    }
    if not last_vehicle and len(words) <= 3 and any(w in words for w in vague_words):
        return True
    if not last_vehicle and vehicle and len(words) <= 1:
        return True
    if not last_vehicle and lower in {vehicle.lower(), f"hyundai {vehicle.lower()}"}:
        return True
    return False


def clarification_message(message: str, ctx: dict[str, Any] | None = None) -> str:
    ctx = ctx or {}
    vehicle = detect_vehicle(message) or ctx.get("last_vehicle") or ""
    topic = detect_topic(message) or ctx.get("pending_topic") or ""

    if not vehicle and not ctx.get("last_vehicle") and (topic or is_vague_query(message)):
        hint = TOPIC_HINTS.get(topic, "I'll then answer your question.")
        return VEHICLE_MODEL_PROMPT.format(topic_hint=hint)

    if vehicle:
        return CLARIFICATION_MESSAGE.format(vehicle=vehicle)
    return GENERIC_CLARIFICATION


def prepare_clarification_context(ctx: dict[str, Any], message: str) -> dict[str, Any]:
    """Remember what the user wanted so the next reply can be answered."""
    topic = detect_topic(message)
    vehicle = detect_vehicle(message)
    if vehicle and not topic and _is_vehicle_only_query(message):
        ctx["pending_vehicle"] = vehicle
    elif topic and not vehicle and not ctx.get("last_vehicle"):
        ctx["pending_topic"] = topic
    return ctx


def detect_topic(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ("price", "cost", "lakh", "rupee")):
        return "price"
    if any(k in lower for k in ("mileage", "milage", "kmpl", "km/l", "fuel efficiency")):
        return "mileage"
    if any(k in lower for k in ("seat", "seater", "seating")):
        return "seats"
    if any(k in lower for k in ("feature", "specification", "specs")):
        return "features"
    # Booking intent only when clearly about scheduling, not substring noise
    if re.search(r"\b(book|booking)\b", lower) and re.search(
        r"\b(slot|slots|timing|timings|schedule|appointment|test drive)\b", lower
    ):
        return "booking"
    if any(k in lower for k in ("compare", "vs", "versus")):
        return "compare"
    if any(k in lower for k in ("warranty", "service")):
        return "service"
    return ""


def is_vague_query(text: str) -> bool:
    lower = text.lower().strip()
    if detect_vehicle(lower) and detect_topic(lower):
        return False
    if any(p in lower for p in VAGUE_PHRASES):
        return True
    if re.search(r"\b(it|its|it's)\b", lower):
        return True
    return len(lower.split()) <= 4 and not detect_vehicle(lower)


def _vehicle_name(ctx: dict[str, Any], message: str) -> str:
    return detect_vehicle(message) or ctx.get("last_vehicle") or ""


def _topic_query(vehicle: str, topic: str) -> str:
    queries = {
        "price": f"What is the price of Hyundai {vehicle}?",
        "mileage": f"What is the mileage of Hyundai {vehicle}?",
        "seats": f"What is the seating capacity of Hyundai {vehicle}?",
        "features": f"What are the features of Hyundai {vehicle}?",
        "booking": f"Can I schedule a test drive for Hyundai {vehicle}?",
    }
    return queries.get(topic, f"Tell me about Hyundai {vehicle}")


def _extract_vehicles_from_text(text: str) -> list[str]:
    lower = normalize_message(text).lower()
    found: list[str] = []
    for model in sorted(VEHICLE_MODELS, key=len, reverse=True):
        if model in lower:
            name = _display_name(model)
            if name not in found:
                found.append(name)
    return found


def _compare_search_query(message: str, ctx: dict[str, Any]) -> str:
    lower = normalize_message(message).lower()
    vehicles = _extract_vehicles_from_text(message)
    last = ctx.get("last_vehicle") or ""

    compare_partner_words = ("with", "and", "vs", "versus", "against")
    has_partner = any(w in lower for w in compare_partner_words)
    vague_ref = any(
        p in lower for p in ("this car", "my car", "that car", "the car")
    ) or re.search(r"\bit\b", lower)

    if last and last not in vehicles and vague_ref and len(vehicles) >= 1:
        partner = vehicles[0]
        return f"Compare Hyundai {last} and {partner}"

    if last and last not in vehicles and (vague_ref or (has_partner and len(vehicles) == 1)):
        vehicles.insert(0, last)

    for model in VEHICLE_MODELS:
        if model in lower:
            name = _display_name(model)
            if name not in vehicles:
                vehicles.append(name)

    if len(vehicles) >= 2:
        return f"Compare Hyundai {vehicles[0]} and {vehicles[1]}"
    if len(vehicles) == 1:
        if "verna" in lower and vehicles[0] != "Verna":
            return f"Compare Hyundai {vehicles[0]} and Verna"
        if "venue" in lower and vehicles[0] != "Venue":
            return f"Compare Hyundai {vehicles[0]} and Venue"
        if "creta" in lower and vehicles[0] != "Creta":
            return f"Compare Hyundai {vehicles[0]} and Creta"
        if "alcazar" in lower and vehicles[0] != "Alcazar":
            return f"Compare Hyundai {vehicles[0]} and Alcazar"
        if "tucson" in lower and vehicles[0] != "Tucson":
            return f"Compare Hyundai {vehicles[0]} and Tucson"
    return message


def enrich_search_query(message: str, ctx: dict[str, Any]) -> str:
    """Normalize queries so semantic search finds the right FAQ."""
    message = normalize_message(message)
    lower = message.lower().strip()
    vehicle = _vehicle_name(ctx, message)

    if vehicle:
        if detect_topic(message) == "compare":
            return _compare_search_query(message, ctx)
        if "tell me about" in lower:
            return f"Tell me about Hyundai {vehicle}"
        if re.match(r"^[\w\s]+\?$", message.strip()) and len(lower.split()) <= 3:
            return f"Tell me about Hyundai {vehicle}"
        topic = detect_topic(message)
        if topic:
            return _topic_query(vehicle, topic)

    return message


def resolve_query(message: str, ctx: dict[str, Any]) -> str:
    """Expand vague queries using session context (e.g. 'its mileage' -> Creta mileage)."""
    message = normalize_message(message)
    if mentions_unknown_vehicle(message) or is_low_signal_query(message):
        return message
    lower = message.lower()
    vehicle = _vehicle_name(ctx, message)
    current_topic = detect_topic(message)
    pending_topic = ctx.get("pending_topic") or ""
    pending_vehicle = ctx.get("pending_vehicle") or ""

    if pending_vehicle and current_topic:
        vehicle = pending_vehicle
        ctx["pending_vehicle"] = ""
        return _topic_query(vehicle, current_topic)

    if pending_topic and detect_vehicle(message) and not current_topic:
        vehicle = detect_vehicle(message)
        ctx["pending_topic"] = ""
        return _topic_query(vehicle, pending_topic)

    if current_topic == "compare":
        if not vehicle and not ctx.get("last_vehicle"):
            return message
        return _compare_search_query(message, ctx)

    # Current message explicitly asks about a topic — prefer it over stale context
    if current_topic and vehicle:
        return _topic_query(vehicle, current_topic)

    if vehicle and current_topic:
        return _topic_query(vehicle, current_topic)

    if vehicle and not is_vague_query(message):
        return enrich_search_query(message, ctx)

    if not vehicle:
        return enrich_search_query(message, ctx)

    # Vague follow-up — use topic from message first, then session
    if current_topic:
        return _topic_query(vehicle, current_topic)
    if "mileage" in lower or "milage" in lower:
        return _topic_query(vehicle, "mileage")
    if "seat" in lower or "seater" in lower:
        return _topic_query(vehicle, "seats")
    if "price" in lower or "cost" in lower:
        return _topic_query(vehicle, "price")

    topic = ctx.get("last_topic") or ""
    if topic and topic != "booking":
        return _topic_query(vehicle, topic)
    if "tell me about" in lower or "about my" in lower or "my car" in lower:
        return f"Tell me about Hyundai {vehicle}"
    if re.search(r"\b(it|its|it's)\b", lower):
        return enrich_search_query(f"Hyundai {vehicle} {message}", ctx)

    return enrich_search_query(message, ctx)


def update_context(ctx: dict[str, Any], query: str, answer: str) -> dict[str, Any]:
    query = normalize_message(query)
    explicit_vehicle = detect_vehicle(query)
    compare_query = detect_topic(query) == "compare"
    last_vehicle = ctx.get("last_vehicle") or ""

    if compare_query and last_vehicle and explicit_vehicle and explicit_vehicle != last_vehicle:
        # "compare it with Creta" — keep Venue as anchor, Creta is the partner.
        vehicle = last_vehicle
        ctx["pending_topic"] = ""
        ctx["pending_vehicle"] = ""
    elif explicit_vehicle:
        vehicle = explicit_vehicle
        ctx["pending_topic"] = ""
        ctx["pending_vehicle"] = ""
    elif is_vague_query(query):
        vehicle = last_vehicle
    else:
        vehicle = detect_vehicle(answer) or last_vehicle

    topic = detect_topic(query)
    if not topic and not is_vague_query(query):
        topic = detect_topic(answer)

    if vehicle:
        ctx["last_vehicle"] = vehicle
    if topic:
        ctx["last_topic"] = topic
        if explicit_vehicle and not compare_query:
            ctx["pending_topic"] = ""

    recent = list(ctx.get("recent_queries") or [])
    recent.append(query[:200])
    ctx["recent_queries"] = recent[-8:]
    return ctx

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
    "grandi10": "grand i10",
    "grandi-10": "grand i10",
    "i 20": "i20",
    "i-20": "i20",
}

NOT_OUR_CAR_MESSAGE = "This car is not in our database."

# Common non-Hyundai brands — we only block the brand name, not every competitor model.
COMPETITOR_BRANDS = frozenset({
    "tata",
    "maruti",
    "suzuki",
    "mahindra",
    "honda",
    "toyota",
    "kia",
    "skoda",
    "jeep",
    "ford",
    "nissan",
    "renault",
    "citroen",
    "mg",
    "bmw",
    "mercedes",
    "benz",
    "audi",
    "volkswagen",
    "vw",
    "byd",
    "tesla",
    "jaguar",
    "landrover",
    "land",
    "rover",
    "porsche",
    "ferrari",
    "lamborghini",
    "bentley",
    "rolls",
    "royce",
    "lexus",
    "volvo",
    "mini",
    "fiat",
    "peugeot",
    "isuzu",
    "force",
    "datsun",
})

COMPETITOR_SPELLING_FIXES: dict[str, str] = {
    "mercedies": "mercedes",
    "mercedez": "mercedes",
    "merceds": "mercedes",
    "mercedezbenz": "mercedes",
    "mercedesbenz": "mercedes",
    "bmww": "bmw",
    "bwm": "bmw",
    "beemer": "bmw",
    "beamer": "bmw",
    "audii": "audi",
    "toyata": "toyota",
    "hunda": "honda",
    "maruthi": "maruti",
    "suzuky": "suzuki",
}

TOPIC_QUERY_TERMS = {
    "price",
    "cost",
    "lakh",
    "rupee",
    "mileage",
    "milage",
    "kmpl",
    "fuel",
    "efficiency",
    "seat",
    "seats",
    "seater",
    "seating",
    "capacity",
    "compare",
    "comparison",
    "versus",
    "difference",
    "between",
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
    "range",
    "many",
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
    "also",
    "any",
    "are",
    "at",
    "be",
    "by",
    "can",
    "car",
    "cars",
    "could",
    "detail",
    "details",
    "do",
    "does",
    "for",
    "from",
    "get",
    "give",
    "have",
    "help",
    "hyundai",
    "i",
    "in",
    "info",
    "information",
    "is",
    "know",
    "like",
    "me",
    "more",
    "my",
    "need",
    "of",
    "on",
    "or",
    "please",
    "show",
    "some",
    "tell",
    "the",
    "to",
    "want",
    "wanna",
    "gonna",
    "gimme",
    "lemme",
    "pls",
    "plz",
    "hey",
    "yeah",
    "share",
    "explain",
    "learn",
    "describe",
    "deal",
    "what",
    "when",
    "where",
    "which",
    "who",
    "how",
    "many",
    "much",
    "this",
    "that",
    "with",
    "it",
    "its",
    "you",
    "your",
    "would",
}


def build_known_hyundai_terms() -> frozenset[str]:
    """Lowercase tokens for every Hyundai model in our FAQ database."""
    terms: set[str] = set()
    for model in VEHICLE_MODELS:
        terms.add(model.lower())
        for part in model.split():
            if len(part) >= 3:
                terms.add(part)
    for alias, canonical in VEHICLE_ALIASES.items():
        terms.add(alias.lower())
        terms.add(canonical.lower())
        for part in alias.split():
            if len(part) >= 3:
                terms.add(part)
    terms.add("i20")
    return frozenset(terms)


_KNOWN_HYUNDAI_TERMS: frozenset[str] | None = None


def get_known_hyundai_terms() -> frozenset[str]:
    global _KNOWN_HYUNDAI_TERMS
    if _KNOWN_HYUNDAI_TERMS is None:
        _KNOWN_HYUNDAI_TERMS = build_known_hyundai_terms()
    return _KNOWN_HYUNDAI_TERMS


def _model_in_text(model: str, text: str) -> bool:
    """Match a model name with word boundaries — avoids 'venue' inside 'avenue'."""
    if " " in model:
        return model in text
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(model)}(?![a-z0-9])", text))


def is_our_hyundai_model(term: str) -> bool:
    """True when a token matches a Hyundai model in our database."""
    token = term.lower().strip()
    if len(token) < 2:
        return False
    if token in get_known_hyundai_terms():
        return True
    if token == "i20":
        return True
    if len(token) >= 4:
        match = get_close_matches(token, VEHICLE_MODELS, n=1, cutoff=0.86)
        if match:
            return True
    for model in VEHICLE_MODELS:
        if len(token) >= 4 and len(model) >= 4 and (token in model or model in token):
            return True
        if _model_in_text(model, token) or _model_in_text(token, model):
            return True
    for alias in VEHICLE_ALIASES:
        alias_l = alias.lower()
        if token == alias_l or token == VEHICLE_ALIASES[alias]:
            return True
        if len(token) >= 4 and len(alias_l) >= 4 and (token in alias_l or alias_l in token):
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


def _is_competitor_token(token: str) -> bool:
    """True when a token names or closely misspells a non-Hyundai automaker."""
    normalized = token.lower().strip()
    if not normalized:
        return False
    if normalized in COMPETITOR_BRANDS:
        return True
    if normalized in COMPETITOR_SPELLING_FIXES:
        return True
    # Short/common words (e.g. "for") must not fuzzy-match brands like "ford".
    if len(normalized) >= 5:
        if get_close_matches(normalized, list(COMPETITOR_BRANDS), n=1, cutoff=0.84):
            return True
    return False


def mentions_competitor_brand(query: str) -> bool:
    """True when the user names a known non-Hyundai automaker."""
    tokens = re.findall(r"[a-z0-9]+", normalize_message(query).lower())
    return any(_is_competitor_token(token) for token in tokens)


def unknown_vehicle_terms(query: str) -> list[str]:
    """Non-Hyundai model-like tokens in the query (original word order)."""
    normalized = normalize_message(query)
    return [
        term
        for term in re.findall(r"[a-z0-9]+", normalized.lower())
        if term not in QUERY_STOPWORDS
        and term not in TOPIC_QUERY_TERMS
        and term not in GENERIC_AUTO_TERMS
        and not is_our_hyundai_model(term)
    ]


def unknown_vehicle_message(query: str) -> str:
    """User-facing message when a non-Hyundai car is mentioned."""
    return NOT_OUR_CAR_MESSAGE


def search_result_matches_query(query: str, answer: str) -> bool:
    """
    False when semantic search returns an FAQ that does not mention the car
    the user asked about (e.g. Creta price for 'price of bmw').
    """
    if mentions_unknown_vehicle(query):
        return False
    vehicle = detect_vehicle(query)
    answer_lower = answer.lower()
    if vehicle and vehicle.lower() in answer_lower:
        return True
    entity_terms = query_entity_terms(query)
    if not entity_terms:
        return True
    blob = f"{query} {answer}".lower()
    return all(term in blob for term in entity_terms)


def mentions_unknown_vehicle(query: str) -> bool:
    """
    True when the user names a car that is not in our Hyundai model list.
    Generic questions (e.g. 'what is the price') return False — clarification handles those.
    """
    if mentions_competitor_brand(query):
        return True
    unknown = unknown_vehicle_terms(query)
    if not unknown:
        return False
    # A valid Hyundai model is present — only reject when another car-like name appears.
    if detect_vehicle(query):
        return bool(unknown)
    return bool(unknown)


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
    if is_vague_query(stripped) or re.search(r"\b(it|its|it's)\b", stripped):
        return False
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

ABOUT_INTENT_PATTERNS: tuple[str, ...] = (
    r"tell me about",
    r"tell me more about",
    r"can you tell me about",
    r"could you tell me about",
    r"please tell me about",
    r"want to know about",
    r"wanna know about",
    r"wanted to know about",
    r"like to know about",
    r"know about",
    r"learn about",
    r"info on",
    r"info about",
    r"information on",
    r"information about",
    r"what about",
    r"how about",
    r"more about",
    r"details about",
    r"details on",
    r"give me info on",
    r"give me information on",
    r"i want to know about",
    r"share about",
    r"explain about",
    r"describe",
)


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


_GLUED_TOPIC_SPLITS: tuple[tuple[str, str], ...] = (
    ("priceof", "price of"),
    ("costof", "cost of"),
    ("mileageof", "mileage of"),
    ("pricefor", "price for"),
    ("costfor", "cost for"),
    ("detailfor", "detail for"),
    ("detailsfor", "details for"),
    ("infoon", "info on"),
    ("aboutthe", "about the"),
    ("priceforgrand", "price for grand"),
    ("forgrand", "for grand"),
    ("pricegrand", "price grand"),
)


def _split_glued_topic_words(text: str) -> str:
    """Split tokens like 'pricefor' into 'price for'."""
    result = text.lower()
    for token in set(re.findall(r"[a-z0-9]+", result)):
        for glued, expanded in _GLUED_TOPIC_SPLITS:
            if token == glued:
                result = result.replace(token, expanded)
                break
        else:
            for prefix in (
                "price",
                "cost",
                "mileage",
                "detail",
                "details",
                "info",
                "about",
                "for",
            ):
                if token.startswith(prefix) and len(token) > len(prefix):
                    suffix = token[len(prefix):]
                    if suffix in {"for", "of", "on", "grand"}:
                        result = result.replace(token, f"{prefix} {suffix}", 1)
                        break
                    if suffix in VEHICLE_MODELS or suffix in VEHICLE_ALIASES:
                        result = result.replace(token, f"{prefix} {suffix}", 1)
                        break
    return re.sub(r"\s+", " ", result).strip()


_GLUE_PREFIXES = frozenset({
    "",
    "for",
    "of",
    "on",
    "at",
    "hyundai",
    "price",
    "cost",
    "mileage",
    "detail",
    "details",
    "about",
    "info",
    "grand",
    "the",
    "my",
    "new",
})


def _split_model_from_token(token: str, model: str) -> str | None:
    """Pull a model name out of a glued token only when the glue is intentional."""
    if model not in token or token == model:
        return None
    idx = token.find(model)
    prefix = token[:idx]
    suffix = token[idx + len(model) :]
    if prefix and prefix not in _GLUE_PREFIXES:
        for glued, _expanded in _GLUED_TOPIC_SPLITS:
            if prefix.endswith(glued.replace(" ", "")) or prefix == glued.replace(" ", ""):
                break
        else:
            if not any(prefix.endswith(p) for p in ("price", "cost", "mileage", "detail", "for")):
                return None
    if suffix and suffix not in {"", "price", "mileage", "cost"}:
        return None
    parts = [part for part in (prefix, model, suffix) if part]
    return " ".join(parts)


def _split_glued_vehicle_names(text: str) -> str:
    """Split tokens like 'forTucson' or 'priceofcreta' into separate words."""
    result = text.lower()
    models_and_aliases = sorted(
        {*VEHICLE_MODELS, *VEHICLE_ALIASES.keys()},
        key=len,
        reverse=True,
    )
    for model in models_and_aliases:
        for match in re.finditer(r"[a-z0-9]+", result):
            token = match.group()
            split_token = _split_model_from_token(token, model)
            if split_token:
                result = result.replace(token, split_token, 1)
    result = _split_glued_topic_words(result)
    return re.sub(r"\s+", " ", result).strip()


def normalize_message(text: str) -> str:
    """Fix common typos and normalize vehicle aliases before search."""
    lower = text.lower().strip()
    lower = re.sub(r"'s\b", " is", lower)
    lower = re.sub(r"'re\b", " are", lower)
    lower = re.sub(r"'ll\b", " will", lower)
    lower = re.sub(r"'ve\b", " have", lower)
    lower = re.sub(r"'", "", lower)
    lower = _split_glued_vehicle_names(lower)
    for alias, canonical in sorted(VEHICLE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        lower = lower.replace(alias, canonical)
    tokens = re.findall(r"[a-z0-9]+", lower)
    fixed_tokens: list[str] = []
    for token in tokens:
        if token in COMPETITOR_SPELLING_FIXES:
            fixed_tokens.append(COMPETITOR_SPELLING_FIXES[token])
            continue
        if token in SPELLING_FIXES:
            fixed_tokens.append(SPELLING_FIXES[token])
            continue
        if _is_competitor_token(token):
            fixed_tokens.append(token)
            continue
        fixed_tokens.append(token)
    if not fixed_tokens:
        return text.strip()
  # Preserve original casing loosely by rebuilding from fixed tokens
    return " ".join(fixed_tokens)


def detect_vehicle(text: str) -> str:
    lower = normalize_message(text).lower()
    for alias, canonical in sorted(VEHICLE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if _model_in_text(alias, lower):
            return _display_name(canonical)
    for model in sorted(VEHICLE_MODELS, key=len, reverse=True):
        if _model_in_text(model, lower):
            return _display_name(model)
    return ""


def _display_name(model: str) -> str:
    if model == "i20":
        return "i20"
    if model == "grand i10":
        return "Grand I10"
    if model == "nios":
        return "Nios"
    if model == "ioniq":
        return "Ioniq"
    return model.title()


def _has_about_intent(text: str) -> bool:
    """True when the user wants general information about a car (not just naming it)."""
    lower = normalize_message(text).lower()
    if any(re.search(pattern, lower) for pattern in ABOUT_INTENT_PATTERNS):
        return True
  # Short forms: "about creta", "about hyundai creta"
    if detect_vehicle(text) and re.search(r"\babout\b", lower):
        return True
    return False


def _is_vehicle_only_query(message: str) -> bool:
    normalized = normalize_message(message)
    if _has_about_intent(normalized):
        return False
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

    if vehicle and _has_about_intent(normalized):
        return False

    if _is_vehicle_only_query(normalized) and not pending_topic:
        return True

    if is_vague_query(normalized) and not last_vehicle and not (vehicle and _has_about_intent(normalized)):
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
    if not last_vehicle and not vehicle and len(words) <= 3 and any(w in words for w in vague_words):
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
    if vehicle and not topic and _is_vehicle_only_query(message) and not _has_about_intent(message):
        ctx["pending_vehicle"] = vehicle
    elif topic and not vehicle and not ctx.get("last_vehicle"):
        ctx["pending_topic"] = topic
    return ctx


def detect_topic(text: str) -> str:
    lower = normalize_message(text).lower()
    if any(k in lower for k in ("price", "cost", "lakh", "rupee", "how much")):
        return "price"
    if any(k in lower for k in ("mileage", "milage", "kmpl", "km/l", "fuel efficiency")):
        return "mileage"
    if any(k in lower for k in ("seat", "seater", "seating", "how many seats", "seating capacity")):
        return "seats"
    if detect_vehicle(text) and _has_about_intent(text):
        return "about"
    if any(
        k in lower
        for k in ("feature", "specification", "specs", "detail", "details", "information")
    ):
        return "features"
    # Booking intent only when clearly about scheduling, not substring noise
    if re.search(r"\b(book|booking)\b", lower) and re.search(
        r"\b(slot|slots|timing|timings|schedule|appointment|test drive)\b", lower
    ):
        return "booking"
    if any(k in lower for k in ("compare", "vs", "versus", "difference between")):
        return "compare"
    if any(k in lower for k in ("warranty", "service")):
        return "service"
    return ""


def is_vague_query(text: str) -> bool:
    lower = text.lower().strip()
    if detect_vehicle(lower) and (_has_about_intent(lower) or detect_topic(lower)):
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
        "about": f"Tell me about Hyundai {vehicle}",
        "booking": f"Can I schedule a test drive for Hyundai {vehicle}?",
    }
    return queries.get(topic, f"Tell me about Hyundai {vehicle}")


def _extract_vehicles_from_text(text: str) -> list[str]:
    lower = normalize_message(text).lower()
    found: list[str] = []
    for model in sorted(VEHICLE_MODELS, key=len, reverse=True):
        if _model_in_text(model, lower):
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
        if _model_in_text(model, lower):
            name = _display_name(model)
            if name not in vehicles:
                vehicles.append(name)

    if len(vehicles) >= 2:
        return f"Compare Hyundai {vehicles[0]} and {vehicles[1]}"
    if len(vehicles) == 1:
        if _model_in_text("verna", lower) and vehicles[0] != "Verna":
            return f"Compare Hyundai {vehicles[0]} and Verna"
        if _model_in_text("venue", lower) and vehicles[0] != "Venue":
            return f"Compare Hyundai {vehicles[0]} and Venue"
        if _model_in_text("creta", lower) and vehicles[0] != "Creta":
            return f"Compare Hyundai {vehicles[0]} and Creta"
        if _model_in_text("alcazar", lower) and vehicles[0] != "Alcazar":
            return f"Compare Hyundai {vehicles[0]} and Alcazar"
        if _model_in_text("tucson", lower) and vehicles[0] != "Tucson":
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
        if _has_about_intent(lower) or "tell me about" in lower or re.search(
            r"\b(detail|details|more\s+info|more\s+information)\b", lower
        ):
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
    if "tell me about" in lower or "about my" in lower or "my car" in lower or "what about it" in lower:
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

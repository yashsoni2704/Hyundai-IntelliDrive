"""Detect user queries about test-drive slot availability."""

import re

SLOT_PATTERNS = [
    "available timing",
    "available timings",
    "available time",
    "available slot",
    "available slots",
    "free slot",
    "free slots",
    "next slot",
    "next slots",
    "timing for today",
    "timings for today",
    "slots for today",
    "what are available timings",
    "show available timings",
    "show timing",
    "show timings",
    "show slot",
    "show slots",
    "booking time",
    "test drive time",
    "test drive timing",
    "schedule timing",
    "when can i book",
    "book slot",
    "book a slot",
    "want to book slot",
]

# If user asks about these, never treat as slot availability
FAQ_BLOCKERS = [
    "mileage",
    "milage",
    "kmpl",
    "price",
    "cost",
    "lakh",
    "seat",
    "seater",
    "seating",
    "how many",
    "feature",
    "specification",
    "warranty",
    "engine",
    "safety",
    "colour",
    "color",
    "compare",
    "versus",
    "tell me about",
]


def is_slot_availability_query(message: str) -> bool:
    """Return True only when the user is clearly asking about bookable time slots."""
    q = message.lower().strip()

    if any(blocker in q for blocker in FAQ_BLOCKERS):
        return False

    if any(p in q for p in SLOT_PATTERNS):
        return True

    has_slot_word = bool(re.search(r"\bslots?\b", q))
    has_timing = bool(re.search(r"\b(timings?|availability|schedule|appointment)\b", q))
    has_when = "when can" in q or "what time" in q or "which time" in q
    has_today = "today" in q or "tomorrow" in q

    if has_slot_word and (has_today or has_timing or "test drive" in q):
        return True

    if has_timing and has_today:
        return True

    if has_when and ("book" in q or "test drive" in q):
        return True

    return False

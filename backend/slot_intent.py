"""Detect user queries about test-drive slot availability."""

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
    "what time",
    "which time",
    "when can i",
    "show timing",
    "show timings",
    "show slot",
    "show slots",
    "booking time",
    "test drive time",
    "test drive timing",
    "schedule timing",
]

TIMING_KEYWORDS = [
    "timing",
    "timings",
    "time slot",
    "timeslot",
    "slot",
    "slots",
    "available",
    "availability",
    "schedule",
    "appointment",
    "book",
    "booking",
]


def is_slot_availability_query(message: str) -> bool:
    """Return True when the user is asking about bookable time slots."""
    q = message.lower().strip()
    if any(p in q for p in SLOT_PATTERNS):
        return True
    has_timing = any(k in q for k in TIMING_KEYWORDS)
    has_context = any(w in q for w in ["today", "test drive", "drive", "book", "tomorrow"])
    return has_timing and has_context

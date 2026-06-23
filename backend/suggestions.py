"""Contextual follow-up suggestions after chat responses."""

from __future__ import annotations

SUGGESTION_POOL = [
    {"label": "Book a test drive", "action": "book_test_drive", "id": "book_test_drive"},
    {"label": "View my bookings", "action": "my_bookings", "id": "my_bookings"},
    {"label": "What is the price of Hyundai Creta?", "action": "chat", "id": "price_creta"},
    {"label": "Does Hyundai offer electric vehicles?", "action": "chat", "id": "ev_offer"},
    {"label": "Which Hyundai SUV is best for families?", "action": "chat", "id": "family_suv"},
    {"label": "What is the mileage of Hyundai Venue?", "action": "chat", "id": "venue_mileage"},
    {"label": "Compare Creta and Venue", "action": "chat", "query": "Compare Hyundai Creta and Venue", "id": "compare_creta_venue"},
    {"label": "View available timings", "action": "chat", "query": "What are available timings for today?", "id": "view_timings"},
    {"label": "What cars are available?", "action": "chat", "query": "What Hyundai cars are currently available?", "id": "cars_available"},
    {"label": "Can I schedule a test drive?", "action": "chat", "query": "Can I schedule a test drive?", "id": "schedule_drive"},
    {"label": "Showroom contact details", "action": "chat", "query": "How can I contact Hyundai showroom?", "id": "showroom_contact"},
    {"label": "What is Hyundai warranty?", "action": "chat", "query": "What is Hyundai warranty?", "id": "warranty"},
]

TOPIC_SUGGESTIONS: list[tuple[list[str], list[dict]]] = [
    (
        ["test drive", "test-drive", "schedule", "booking", "book"],
        [
            {"label": "View available timings", "action": "chat", "query": "What are available timings for today?", "id": "view_timings"},
            {"label": "Book a test drive now", "action": "book_test_drive", "id": "book_test_drive"},
            {"label": "View my bookings", "action": "my_bookings", "id": "my_bookings"},
        ],
    ),
    (
        ["creta", "price", "cost", "lakh"],
        [
            {"label": "Book Creta test drive", "action": "book_test_drive", "vehicle": "Creta", "id": "book_creta"},
            {"label": "Creta mileage", "action": "chat", "query": "What is the mileage of Hyundai Creta?", "id": "creta_mileage"},
            {"label": "Compare Creta and Venue", "action": "chat", "query": "Compare Hyundai Creta and Venue", "id": "compare_creta_venue"},
        ],
    ),
    (
        ["electric", "ev", "ioniq", "kona"],
        [
            {"label": "Book EV test drive", "action": "book_test_drive", "vehicle": "Ioniq 5", "id": "book_ev"},
            {"label": "EV charging options", "action": "chat", "query": "Does Hyundai offer electric vehicles?", "id": "ev_offer"},
        ],
    ),
    (
        ["suv", "venue", "alcazar", "family"],
        [
            {"label": "Book SUV test drive", "action": "book_test_drive", "vehicle": "SUV", "id": "book_suv"},
            {"label": "Best family SUV", "action": "chat", "query": "Which Hyundai SUV is best for families?", "id": "family_suv"},
        ],
    ),
    (
        ["timing", "slot", "available", "appointment"],
        [
            {"label": "Book a test drive", "action": "book_test_drive", "id": "book_test_drive"},
            {"label": "What is the price of Hyundai Creta?", "action": "chat", "id": "price_creta"},
        ],
    ),
]


def _suggestion_id(item: dict) -> str:
    return item.get("id") or item.get("label", "")


def _text_contains(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(k in lower for k in keywords)


def _filter_used(items: list[dict], used_ids: set[str]) -> list[dict]:
    return [dict(item) for item in items if _suggestion_id(item) not in used_ids]


def get_follow_up_suggestions(
    query: str,
    answer: str,
    found: bool,
    used_suggestion_ids: list[str] | None = None,
    context: dict | None = None,
) -> list[dict]:
    """Return up to 4 contextual suggestions, excluding ones the user already used."""
    used_ids = set(used_suggestion_ids or [])
    ctx = context or {}
    vehicle = (ctx.get("last_vehicle") or "").lower()
    combined = f"{query} {answer}"
    if vehicle and vehicle not in combined.lower():
        combined = f"{combined} {vehicle}"
    suggestions: list[dict] = []
    seen_ids: set[str] = set()

    if vehicle:
        vehicle_title = vehicle.title()
        vehicle_items = [
            {"label": f"Book {vehicle_title} test drive", "action": "book_test_drive", "vehicle": vehicle_title, "id": f"book_{vehicle}"},
            {"label": f"{vehicle_title} mileage", "action": "chat", "query": f"What is the mileage of Hyundai {vehicle_title}?", "id": f"{vehicle}_mileage"},
            {"label": f"{vehicle_title} price", "action": "chat", "query": f"What is the price of Hyundai {vehicle_title}?", "id": f"{vehicle}_price"},
        ]
        for item in vehicle_items:
            sid = _suggestion_id(item)
            if sid not in seen_ids and sid not in used_ids:
                suggestions.append(dict(item))
                seen_ids.add(sid)

    for keywords, items in TOPIC_SUGGESTIONS:
        if _text_contains(combined, keywords):
            for item in items:
                sid = _suggestion_id(item)
                if sid not in seen_ids and sid not in used_ids:
                    suggestions.append(dict(item))
                    seen_ids.add(sid)

    if not found:
        fallback = [
            {"label": "View available timings", "action": "chat", "query": "What are available timings for today?", "id": "view_timings"},
            {"label": "Book a test drive", "action": "book_test_drive", "id": "book_test_drive"},
            {"label": "What cars are available?", "action": "chat", "query": "What Hyundai cars are currently available?", "id": "cars_available"},
        ]
        suggestions = _filter_used(fallback, used_ids)

    for item in SUGGESTION_POOL:
        if len(suggestions) >= 4:
            break
        sid = _suggestion_id(item)
        if sid not in seen_ids and sid not in used_ids:
            suggestions.append(dict(item))
            seen_ids.add(sid)

    return suggestions[:4]

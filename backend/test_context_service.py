"""Regression tests for query understanding — run: python -m pytest backend/test_context_service.py"""

from __future__ import annotations

import itertools

import pytest

from context_service import (
    NOT_OUR_CAR_MESSAGE,
    VEHICLE_MODELS,
    _display_name,
    _extract_vehicles_from_text,
    conversational_response,
    default_context,
    detect_topic,
    detect_vehicle,
    is_conversational_query,
    mentions_unknown_vehicle,
    needs_clarification,
    normalize_message,
    resolve_query,
    unknown_vehicle_message,
    update_context,
)

MODELS = ["creta", "venue", "i20", "verna", "alcazar", "tucson", "ioniq", "kona", "aura", "exter", "grand i10", "nios"]

QUERY_TEMPLATES = [
    "give me price for {m}",
    "price for {m}",
    "price of {m}",
    "what is the price of {m}",
    "how much is {m}",
    "{m} price",
    "price{m}",
    "pricefor{m}",
    "mileage of {m}",
    "{m} mileage",
    "fuel efficiency of {m}",
    "tell me about {m}",
    "more details about {m}",
    "can you give me more detail for{m}",
    "can you give me more detail for {m}",
    "seating capacity of {m}",
    "how many seats in {m}",
    "features of {m}",
    "compare {m} and creta",
    "difference between {m} and verna",
]

TYPO_CASES = [
    ("price for tucsan", "Tucson"),
    ("mileage of creeta", "Creta"),
    ("tell me about venu", "Venue"),
    ("price for alcazr", "Alcazar"),
    ("price for i 20", "i20"),
    ("price for grandi10", "Grand I10"),
]

REJECT_QUERIES = [
    "price of bmw",
    "tell me about tata nexon",
    "kia seltos price",
    "maruti swift mileage",
    "honda city price",
    "compare creta with seltos",
]

FALSE_POSITIVE_PHRASES = [
    "avenue price",
    "creation cost",
    "ion channel",
]

GLUED_CASES = [
    ("forTucson", "tucson"),
    ("pricefortucson", "tucson"),
    ("priceforcreta", "creta"),
    ("pricegrandi10", "grand i10"),
    ("priceforgrand i10", "grand i10"),
]


def _all_model_queries() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for model in MODELS:
        display = _display_name(model)
        short = model.replace(" ", "")
        for tmpl in QUERY_TEMPLATES:
            for m in {model, short}:
                pairs.append((tmpl.format(m=m), display))
    return pairs


@pytest.mark.parametrize("query,expected", _all_model_queries())
def test_hyundai_queries_not_rejected(query: str, expected: str) -> None:
    assert not mentions_unknown_vehicle(query), (
        f"Query wrongly rejected: {query!r} -> {unknown_vehicle_message(query)}"
    )
    if "compare" in query or "difference" in query:
        vehicles = _extract_vehicles_from_text(query)
        assert expected in vehicles, f"{expected} not in {vehicles} for {query!r}"
    else:
        assert detect_vehicle(query) == expected, f"vehicle detect failed for {query!r}"


@pytest.mark.parametrize("query,expected", TYPO_CASES)
def test_typo_queries(query: str, expected: str) -> None:
    assert detect_vehicle(query) == expected
    assert not mentions_unknown_vehicle(query)


@pytest.mark.parametrize("query", REJECT_QUERIES)
def test_competitor_queries_rejected(query: str) -> None:
    assert mentions_unknown_vehicle(query), query


@pytest.mark.parametrize("phrase", FALSE_POSITIVE_PHRASES)
def test_no_false_vehicle_match(phrase: str) -> None:
    assert detect_vehicle(phrase) == ""


@pytest.mark.parametrize("raw,needle", GLUED_CASES)
def test_glued_words_split(raw: str, needle: str) -> None:
    assert needle in normalize_message(raw)


@pytest.mark.parametrize("model", MODELS)
def test_resolve_price_query(model: str) -> None:
    display = _display_name(model)
    resolved = resolve_query(f"give me price for {model}", default_context())
    assert display in resolved
    assert "price" in resolved.lower()


@pytest.mark.parametrize("model", MODELS)
def test_resolve_detail_query(model: str) -> None:
    display = _display_name(model)
    resolved = resolve_query(f"more details about {model}", default_context())
    assert display in resolved


def test_vague_mileage_uses_session_vehicle() -> None:
    ctx = default_context()
    ctx["last_vehicle"] = "Creta"
    resolved = resolve_query("its mileage", ctx)
    assert "Creta" in resolved
    assert "mileage" in resolved.lower()


def test_what_about_it_uses_session_vehicle() -> None:
    ctx = default_context()
    ctx["last_vehicle"] = "Verna"
    resolved = resolve_query("what about it", ctx)
    assert "Verna" in resolved


def test_more_followup_rotates_topics_not_repeat_about() -> None:
    """After 'about', 'tell me more' must return price/mileage — not the same about FAQ."""
    ctx = default_context()
    ctx = update_context(
        ctx,
        "i want to know about creta",
        "Hyundai Creta is a popular compact SUV known for bold design.",
    )
    assert ctx["last_vehicle"] == "Creta"
    assert "about" in ctx.get("covered_topics", [])

    r2 = resolve_query("tell more about this", ctx)
    assert "price" in r2.lower()
    ctx = update_context(ctx, "tell more about this", "The Hyundai Creta starts at approximately 11 lakh.")

    r3 = resolve_query("tell me more for this car ?", ctx)
    assert "mileage" in r3.lower()
    ctx = update_context(ctx, "tell me more for this car ?", "The Hyundai Creta delivers approximately 17.4 km/l.")

    r4 = resolve_query("tell me more", ctx)
    assert "seat" in r4.lower() or "seating" in r4.lower()
    assert r2 != "Tell me about Hyundai Creta"
    assert r3 != r2


def test_how_much_detects_price_topic() -> None:
    assert detect_topic("how much is creta") == "price"


def test_compare_phrasing() -> None:
    ctx = default_context()
    resolved = resolve_query("difference between creta and verna", ctx)
    assert "Compare" in resolved or "compare" in resolved.lower()
    assert "Creta" in resolved
    assert "Verna" in resolved


def test_unknown_car_message_constant() -> None:
    assert unknown_vehicle_message("bmw price") == NOT_OUR_CAR_MESSAGE


@pytest.mark.parametrize(
    "query",
    [
        "tell me about i20",
        "Tell me about Hyundai i20",
        "tell me about creta",
        "what about verna",
        "can you tell me about tucson",
        "i want to know about venue",
        "wanna know about kona",
        "could you please tell me about alcazar",
        "give me info on exter",
        "how about aura",
    ],
)
def test_about_queries_never_need_clarification(query: str) -> None:
    ctx = default_context()
    assert not needs_clarification(query, ctx), f"Should answer directly: {query!r}"
    resolved = resolve_query(query, ctx)
    assert detect_vehicle(query) in resolved or "Tell me about" in resolved


@pytest.mark.parametrize("model", VEHICLE_MODELS)
def test_all_models_tell_me_about_no_clarification(model: str) -> None:
    """Every car in our database must answer 'tell me about X' without a clarification loop."""
    display = _display_name(model)
    ctx = default_context()
    for query in (
        f"tell me about {model}",
        f"Tell me about Hyundai {display}",
        f"can you tell me about {model}",
        f"what about {model}",
        f"give me price for {model}",
        f"more details about {model}",
    ):
        assert not needs_clarification(query, ctx), f"Should not clarify: {query!r}"
        assert detect_vehicle(query) == display, f"Wrong vehicle for: {query!r}"
        resolved = resolve_query(query, ctx)
        assert display in resolved, f"Resolve missing {display}: {query!r} -> {resolved!r}"


@pytest.mark.parametrize(
    "query",
    ["okkk", "ok", "thanks", "thank you", "thankyou", "cool", "got it", "nice", "ty", "thx"],
)
def test_conversational_not_treated_as_unknown_car(query: str) -> None:
    assert is_conversational_query(query)
    assert not mentions_unknown_vehicle(query)


def test_conversational_response_keeps_vehicle_context() -> None:
    ctx = default_context()
    ctx["last_vehicle"] = "Creta"
    answer = conversational_response("okkk", ctx)
    assert "Creta" in answer
    assert "not in our database" not in answer.lower()


def test_thank_you_response() -> None:
    ctx = default_context()
    ctx["last_vehicle"] = "Creta"
    answer = conversational_response("thank you", ctx)
    assert "welcome" in answer.lower()
    assert "Creta" in answer


@pytest.mark.parametrize("model", VEHICLE_MODELS)
def test_bare_model_name_needs_clarification(model: str) -> None:
    assert needs_clarification(model, default_context())


def test_for_does_not_match_ford() -> None:
    assert not mentions_unknown_vehicle("give me price for creta")


@pytest.mark.parametrize(
    "word",
    ["for", "on", "at", "by", "can", "more", "detail", "give", "about", "with"],
)
def test_common_words_with_creta_not_rejected(word: str) -> None:
    query = f"{word} creta price"
    assert not mentions_unknown_vehicle(query)


@pytest.mark.parametrize("a,b", list(itertools.combinations(["creta", "venue", "verna", "tucson", "alcazar"], 2))[:10])
def test_compare_queries_not_rejected(a: str, b: str) -> None:
    query = f"compare {a} and {b}"
    assert not mentions_unknown_vehicle(query)
    assert detect_vehicle(query)

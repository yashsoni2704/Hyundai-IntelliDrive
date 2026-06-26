"""Generate and test hundreds of query variants — run: python scripts/fuzz_queries.py"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from context_service import (  # noqa: E402
    VEHICLE_MODELS,
    _display_name,
    default_context,
    detect_topic,
    detect_vehicle,
    mentions_competitor_brand,
    mentions_unknown_vehicle,
    needs_clarification,
    normalize_message,
    is_conversational_query,
    resolve_query,
    unknown_vehicle_terms,
    update_context,
)
from scripts.human_patterns import (  # noqa: E402
    HUMAN_ABOUT_PATTERNS,
    HUMAN_CASUAL_PATTERNS,
    HUMAN_MILEAGE_PATTERNS,
    HUMAN_PRICE_PATTERNS,
)

MODELS = {
    "creta": "Creta",
    "venue": "Venue",
    "i20": "i20",
    "verna": "Verna",
    "alcazar": "Alcazar",
    "tucson": "Tucson",
    "ioniq": "Ioniq",
    "kona": "Kona",
    "aura": "Aura",
    "exter": "Exter",
    "grand i10": "Grand I10",
    "nios": "Nios",
}

TEMPLATES = [
    "give me price for {m}",
    "price for {m}",
    "price of {m}",
    "what is the price of {m}",
    "how much is {m}",
    "{m} price",
    "price{m}",
    "pricefor{m}",
    "for{m} price",
    "mileage of {m}",
    "{m} mileage",
    "what is mileage of {m}",
    "fuel efficiency of {m}",
    "tell me about {m}",
    "i want to know about {m}",
    "more details about {m}",
    "can you give me more detail for{m}",
    "can you give me more detail for {m}",
    "details on {m} please",
    "features of {m}",
    "specs of {m}",
    "seating capacity of {m}",
    "how many seats in {m}",
    "hyundai {m}",
    "{m}",
    "about {m}",
    "info on {m}",
    "need info on {m}",
    "could you tell me more about {m}",
]

TYPO_MAP = {
    "creta": ["creeta", "kreta", "cret"],
    "venue": ["venu", "vunue"],
    "tucson": ["tucsan", "tuscon", "tuscan"],
    "alcazar": ["alcazr", "alacazar"],
    "verna": ["vernaa", "verana"],
    "exter": ["extar"],
    "i20": ["i 20", "i-20"],
}

COMPETITOR_SHOULD_REJECT = [
    "price of bmw",
    "tata nexon price",
    "maruti swift mileage",
    "kia seltos vs creta",
    "honda city price",
    "toyota fortuner",
    "mg hector price",
    "audi a4 price",
]

COMPETITOR_SHOULD_ACCEPT_HYUNDAI = [
    "compare creta with seltos",  # has hyundai + competitor model name
]


def generate_queries() -> list[tuple[str, str]]:
    """Return (query, expected_vehicle_display_name) pairs."""
    pairs: list[tuple[str, str]] = []
    for model_key, display in MODELS.items():
        short = model_key.replace(" ", "")
        for tmpl in TEMPLATES:
            q = tmpl.format(m=model_key if "{" in tmpl else short)
            pairs.append((q, display))
            q2 = tmpl.format(m=short)
            if q2 != q:
                pairs.append((q2, display))
        for typo in TYPO_MAP.get(model_key, []):
            pairs.append((f"price for {typo}", display))
            pairs.append((f"mileage of {typo}", display))
            pairs.append((f"tell me about {typo}", display))
    return pairs


def generate_human_queries() -> list[tuple[str, str]]:
    """Casual / polite / normal human phrasings per model."""
    pairs: list[tuple[str, str]] = []
    all_patterns = (
        HUMAN_ABOUT_PATTERNS
        + HUMAN_PRICE_PATTERNS
        + HUMAN_MILEAGE_PATTERNS
        + HUMAN_CASUAL_PATTERNS
    )
    for model_key, display in MODELS.items():
        short = model_key.replace(" ", "")
        for tmpl in all_patterns:
            for m, d in ((model_key, display), (short, display)):
                try:
                    pairs.append((tmpl.format(m=m, d=d), display))
                except KeyError:
                    pairs.append((tmpl.format(m=m), display))
    return pairs


def main() -> int:
    failures: list[str] = []
    ctx = default_context()

    queries = generate_queries() + generate_human_queries()
    print(f"Testing {len(queries)} Hyundai query variants...")

    for query, expected_vehicle in queries:
        reasons = []

        if mentions_unknown_vehicle(query):
            reasons.append(
                f"wrongly rejected (unknown_terms={unknown_vehicle_terms(query)}, "
                f"competitor={mentions_competitor_brand(query)})"
            )

        vehicle = detect_vehicle(query)
        if vehicle != expected_vehicle:
            reasons.append(f"vehicle={vehicle!r} expected={expected_vehicle!r} norm={normalize_message(query)!r}")

        if not mentions_unknown_vehicle(query):
            resolved = resolve_query(query, dict(ctx))
            topic = detect_topic(query)
            if vehicle and topic and expected_vehicle not in resolved:
                reasons.append(f"resolve missing vehicle: {resolved!r}")

        if reasons:
            failures.append(f"  {query!r} -> {'; '.join(reasons)}")

    print(f"\n--- Competitor rejection tests ({len(COMPETITOR_SHOULD_REJECT)}) ---")
    for q in COMPETITOR_SHOULD_REJECT:
        if not mentions_unknown_vehicle(q):
            failures.append(f"  {q!r} -> should reject competitor but didn't")

    print(f"\n--- False positive competitor brand scan ---")
    common_words = [
        "for", "on", "at", "by", "can", "the", "and", "or", "in", "of",
        "more", "detail", "price", "give", "help", "show", "tell",
        "compare", "versus", "against", "with", "from", "about",
    ]
    for word in common_words:
        q = f"{word} creta price"
        if mentions_competitor_brand(q):
            failures.append(f"  competitor false positive on {q!r}")

    # Substring false positives in detect_vehicle
    print("\n--- Substring false positive scan ---")
    false_positive_phrases = [
        ("avenue price", None),  # should NOT detect Venue
        ("creation cost", None),  # should NOT detect Creta
        ("ion channel", None),  # should NOT detect Ioniq
        ("mini cooper", "Mini"),  # competitor mini brand - should reject
    ]
    for phrase, _ in false_positive_phrases:
        v = detect_vehicle(phrase)
        if phrase == "avenue price" and v == "Venue":
            failures.append(f"  {phrase!r} -> false Venue match")
        if phrase == "creation cost" and v == "Creta":
            failures.append(f"  {phrase!r} -> false Creta match")

    # Compare queries
    print("\n--- Compare query tests ---")
    compare_pairs = list(itertools.combinations(list(MODELS.values())[:8], 2))[:30]
    for a, b in compare_pairs:
        for tmpl in [
            "compare {a} and {b}",
            "compare {a} with {b}",
            "{a} vs {b}",
            "difference between {a} and {b}",
        ]:
            q = tmpl.format(a=a.lower(), b=b.lower())
            if mentions_unknown_vehicle(q):
                failures.append(f"  {q!r} -> wrongly rejected compare")
            elif not detect_vehicle(q):
                # at least one should be detected
                failures.append(f"  {q!r} -> no vehicle detected")

    # Follow-up context tests
    print("\n--- Context follow-up tests ---")
    followups = [
        ("creta", "its mileage", "Creta", "mileage"),
        ("venue", "its price", "Venue", "price"),
        ("tucson", "more details", "Tucson", None),
        ("verna", "what about it", "Verna", None),
        ("alcazar", "and seating?", "Alcazar", "seat"),
    ]
    for model_q, followup, exp_v, exp_topic_word in followups:
        c = default_context()
        c["last_vehicle"] = MODELS.get(model_q, model_q.title())
        if mentions_unknown_vehicle(followup):
            failures.append(f"  followup {followup!r} after {model_q} wrongly rejected")
        resolved = resolve_query(followup, c)
        if exp_v not in resolved:
            failures.append(f"  followup {followup!r} -> {resolved!r} missing {exp_v}")
        if exp_topic_word and exp_topic_word not in resolved.lower():
            failures.append(f"  followup {followup!r} -> {resolved!r} missing topic {exp_topic_word}")

    # About-intent queries must NOT ask for clarification
    print("\n--- About-intent / human phrasing (no clarification loop) ---")
    about_must_answer = [
        "tell me about i20",
        "Tell me about Hyundai i20",
        "what about verna",
        "can you tell me about tucson",
        "i want to know about venue",
        "wanna know about kona",
        "could you please tell me about alcazar",
    ]
    for q in about_must_answer:
        if needs_clarification(q, ctx):
            failures.append(f"  {q!r} -> should answer directly, not clarify")
        resolved = resolve_query(q, dict(ctx))
        vehicle = detect_vehicle(q)
        if vehicle and vehicle not in resolved and "Tell me about" not in resolved:
            failures.append(f"  {q!r} -> bad resolve {resolved!r}")

    # Bare model name should still ask what topic user wants
    print("\n--- Bare model name clarification ---")
    for q in ["i20", "creta", "tucson"]:
        if not needs_clarification(q, ctx):
            failures.append(f"  {q!r} -> bare model should ask clarification")

    # Multi-turn "tell me more" rotation for every model
    print("\n--- More-info follow-up rotation (all models) ---")
    for model_key, display in MODELS.items():
        c = default_context()
        c = update_context(
            c,
            f"tell me about {model_key}",
            f"Hyundai {display} is a great car.",
        )
        r = resolve_query("tell me more", dict(c))
        if "price" not in r.lower():
            failures.append(f"  tell me more after {model_key} -> expected price, got {r!r}")

    # Conversational fillers must never be treated as unknown cars
    print("\n--- Conversational fillers ---")
    filler_ctx = default_context()
    filler_ctx["last_vehicle"] = "Creta"
    for q in ["okkk", "ok", "thanks", "thank you", "cool", "got it", "ty", "thx", "nice", "perfect"]:
        if mentions_unknown_vehicle(q):
            failures.append(f"  {q!r} -> wrongly treated as unknown car")
        if not is_conversational_query(q):
            failures.append(f"  {q!r} -> should be conversational")

    print(f"\n{'='*60}")
    if failures:
        print(f"FAILURES: {len(failures)}")
        for f in failures[:80]:
            print(f)
        if len(failures) > 80:
            print(f"  ... and {len(failures) - 80} more")
        return 1

    print(f"ALL {len(queries)} Hyundai variants + extra tests PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

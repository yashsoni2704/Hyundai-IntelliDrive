"""Add missing per-vehicle and compare FAQs to the knowledge base."""

from __future__ import annotations

import pandas as pd

from config import EXCEL_PATH

VEHICLE_FAQS: dict[str, dict[str, str]] = {
    "Creta": {
        "price": "The Hyundai Creta starts at approximately ₹11 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Creta delivers approximately 17.4 km/l (petrol MT), up to 18.4 km/l (petrol AT), and around 21.4 km/l (diesel MT), depending on variant.",
        "seats": "Hyundai Creta offers 5-seat configuration in all variants.",
        "about": "Hyundai Creta is a popular compact SUV known for bold design, spacious cabin, multiple engine options, and premium features.",
    },
    "Venue": {
        "price": "The Hyundai Venue starts at approximately ₹8.5 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Venue delivers approximately 18.2 km/l (petrol MT) and up to 23.4 km/l (diesel MT), depending on variant.",
        "seats": "Hyundai Venue offers 5-seat configuration in all variants.",
        "about": "Hyundai Venue is a compact SUV with connected car tech, multiple turbo engine options, and city-friendly dimensions.",
    },
    "Verna": {
        "price": "The Hyundai Verna starts at approximately ₹11.5 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Verna delivers approximately 18.6 km/l (petrol MT) and up to 20.6 km/l (diesel MT), depending on variant.",
        "seats": "Hyundai Verna offers 5-seat configuration in all variants.",
        "about": "Hyundai Verna is a premium sedan with ADAS on select variants, spacious rear seat, and refined ride quality.",
    },
    "Alcazar": {
        "price": "The Hyundai Alcazar starts at approximately ₹16.5 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Alcazar delivers approximately 18.1 km/l (petrol MT) and up to 17.5 km/l (diesel MT), depending on variant.",
        "seats": "Hyundai Alcazar is available in 6-seater and 7-seater configurations.",
        "about": "Hyundai Alcazar is a premium 3-row SUV available in 6-seater and 7-seater configurations, with spacious cabin and premium features.",
    },
    "Tucson": {
        "price": "The Hyundai Tucson starts at approximately ₹28 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Tucson offers approximately 16.4 km/l (petrol) and 18.4 km/l (diesel), depending on variant.",
        "seats": "Hyundai Tucson offers 5-seat configuration in all variants.",
        "about": "Hyundai Tucson is a premium mid-size SUV with advanced safety, panoramic sunroof options, and powerful petrol/diesel engines.",
    },
    "i20": {
        "price": "The Hyundai i20 starts at approximately ₹7.5 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai i20 delivers approximately 20.4 km/l (petrol MT) and up to 25.2 km/l (diesel MT), depending on variant.",
        "seats": "Hyundai i20 offers 5-seat configuration in all variants.",
        "about": "Hyundai i20 is a premium hatchback with sharp styling, connected features, and multiple engine-gearbox options.",
    },
    "Exter": {
        "price": "The Hyundai Exter starts at approximately ₹6.5 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Exter delivers approximately 19.4 km/l (petrol MT) and up to 19.2 km/l (petrol AMT), depending on variant.",
        "seats": "Hyundai Exter offers 5-seat configuration in all variants.",
        "about": "Hyundai Exter is a compact SUV with outdoor-focused styling, good ground clearance, and efficient petrol engines.",
    },
    "Aura": {
        "price": "The Hyundai Aura starts at approximately ₹6.5 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Aura delivers approximately 20.5 km/l (petrol MT) and up to 25.4 km/l (diesel MT), depending on variant.",
        "seats": "Hyundai Aura offers 5-seat configuration in all variants.",
        "about": "Hyundai Aura is a compact sedan based on the Grand i10 Nios platform, focused on comfort and fuel efficiency.",
    },
    "Grand I10": {
        "price": "The Hyundai Grand i10 starts at approximately ₹6 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Grand i10 delivers approximately 20.7 km/l (petrol MT) and up to 25.4 km/l (diesel MT), depending on variant.",
        "seats": "Hyundai Grand i10 offers 5-seat configuration in all variants.",
        "about": "Hyundai Grand i10 is a practical hatchback known for easy city driving, low running costs, and comfortable cabin.",
    },
    "Nios": {
        "price": "The Hyundai Grand i10 Nios starts at approximately ₹5.7 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Grand i10 Nios delivers approximately 20.7 km/l (petrol MT) and up to 25.4 km/l (diesel MT), depending on variant.",
        "seats": "Hyundai Grand i10 Nios offers 5-seat configuration in all variants.",
        "about": "Hyundai Grand i10 Nios is a feature-rich hatchback with modern connectivity, efficient engines, and compact dimensions.",
    },
    "Ioniq": {
        "price": "The Hyundai Ioniq 5 starts at approximately ₹45 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Ioniq 5 offers an ARAI-rated range of up to 631 km per charge (variant dependent).",
        "seats": "Hyundai Ioniq 5 offers 5-seat configuration in all variants.",
        "about": "Hyundai Ioniq 5 is a premium electric crossover with ultra-fast charging, spacious cabin, and advanced tech features.",
    },
    "Kona": {
        "price": "The Hyundai Kona Electric starts at approximately ₹24 lakh (ex-showroom). Prices may vary by city and variant.",
        "mileage": "The Hyundai Kona Electric offers an ARAI-rated range of up to 452 km per charge (variant dependent).",
        "seats": "Hyundai Kona Electric offers 5-seat configuration in all variants.",
        "about": "Hyundai Kona Electric is a compact electric SUV with practical range, strong performance, and modern safety features.",
    },
}

COMPARE_FAQS: list[tuple[str, str, str]] = [
    (
        "Alcazar",
        "Creta",
        "Alcazar is a larger 6/7-seater SUV with more cabin space and a third-row option, while Creta is a compact 5-seater SUV. Alcazar suits bigger families; Creta is easier in city traffic and generally more fuel-efficient.",
    ),
    (
        "Alcazar",
        "Verna",
        "Alcazar is a 3-row SUV with higher seating and ground clearance, while Verna is a sedan focused on comfort and highway cruising. Choose Alcazar for family space; Verna for sedan ride and handling.",
    ),
    (
        "Alcazar",
        "Tucson",
        "Alcazar offers 6/7 seats at a more accessible price, while Tucson is a premium 5-seater with more power and advanced features. Alcazar is family-focused; Tucson is for buyers wanting a luxury SUV experience.",
    ),
    (
        "Alcazar",
        "Venue",
        "Alcazar is a full-size 3-row SUV for large families, while Venue is a compact 5-seater SUV for city use. Alcazar provides more space; Venue is easier to park and more affordable.",
    ),
    (
        "Tucson",
        "Creta",
        "Tucson is a larger premium SUV with more power and features, while Creta is a compact SUV with lower price and easier city driving. Tucson suits premium buyers; Creta suits value-focused SUV buyers.",
    ),
    (
        "Tucson",
        "Verna",
        "Tucson is a premium SUV with higher ground clearance and AWD options on select variants, while Verna is a sedan with lower running costs and sedan comfort. Choose based on body style preference.",
    ),
    (
        "Tucson",
        "Venue",
        "Tucson is a mid-size premium SUV, while Venue is a compact SUV. Tucson offers more space and power; Venue is more affordable and city-friendly.",
    ),
    (
        "Venue",
        "Verna",
        "Venue is a compact SUV with higher ground clearance, while Verna is a sedan with more rear-seat comfort and boot space for highway travel. SUV vs sedan preference is the main difference.",
    ),
    (
        "Venue",
        "i20",
        "Venue is a compact SUV with higher ride height, while i20 is a premium hatchback with sportier handling. Venue suits rough roads better; i20 is easier to park and often more fuel-efficient.",
    ),
    (
        "Exter",
        "Venue",
        "Exter is a newer compact SUV with efficient petrol engines, while Venue offers more variant choice and turbo petrol options. Both are 5-seaters; Venue is slightly more feature-rich on top trims.",
    ),
    (
        "Exter",
        "Creta",
        "Exter is an entry compact SUV, while Creta is a larger premium compact SUV with more engine options and space. Creta costs more but offers a more upmarket experience.",
    ),
    (
        "i20",
        "Verna",
        "i20 is a hatchback suited to city driving, while Verna is a sedan with more rear legroom and boot space. Verna is better for families needing sedan comfort on highways.",
    ),
    (
        "Aura",
        "Verna",
        "Aura is an affordable compact sedan, while Verna is a premium sedan with more features and power. Aura focuses on value; Verna on comfort and technology.",
    ),
    (
        "Nios",
        "Grand I10",
        "Grand i10 Nios is the newer hatchback with updated styling and features, while Grand i10 is the earlier generation focused on practicality. Nios is generally preferred for latest tech and design.",
    ),
    (
        "Creta",
        "Verna",
        "Creta is a compact SUV with higher ground clearance and SUV styling, while Verna is a sedan with lower running costs and sedan comfort. Choose Creta for SUV road presence; Verna for sedan ride and boot space.",
    ),
    (
        "Exter",
        "Verna",
        "Exter is a compact SUV with higher ground clearance and outdoor styling, while Verna is a sedan with more rear-seat comfort for highway travel. Choose based on SUV vs sedan preference.",
    ),
    (
        "Exter",
        "Tucson",
        "Exter is an affordable compact SUV for city use, while Tucson is a larger premium SUV with more power and features. Tucson suits buyers wanting a premium experience; Exter suits budget-focused SUV buyers.",
    ),
    (
        "Ioniq",
        "Kona",
        "Ioniq 5 is a larger premium EV with longer range and ultra-fast charging, while Kona Electric is a compact EV with lower price. Ioniq 5 suits premium EV buyers; Kona suits city-focused EV users.",
    ),
]

TOPIC_QUESTIONS = {
    "price": "What is the price of Hyundai {vehicle}?",
    "mileage": "What is the mileage of Hyundai {vehicle}?",
    "seats": "What is the seating capacity of Hyundai {vehicle}?",
    "about": "Tell me about Hyundai {vehicle}",
}


def _has_question(existing: set[str], question: str) -> bool:
    return question.strip().lower() in existing


def build_new_rows(existing: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for vehicle, topics in VEHICLE_FAQS.items():
        for topic, answer in topics.items():
            question = TOPIC_QUESTIONS[topic].format(vehicle=vehicle)
            if not _has_question(existing, question):
                rows.append({"Question": question, "Answer": answer})
                existing.add(question.lower())

    for left, right, answer in COMPARE_FAQS:
        question = f"Compare Hyundai {left} and {right}"
        if not _has_question(existing, question):
            rows.append({"Question": question, "Answer": answer})
            existing.add(question.lower())

    return rows


def main() -> None:
    df = pd.read_excel(EXCEL_PATH)
    existing = {str(q).strip().lower() for q in df["Question"]}
    new_rows = build_new_rows(existing)
    if not new_rows:
        print("No new FAQs to add.")
        return
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    df.to_excel(EXCEL_PATH, index=False)
    print(f"Added {len(new_rows)} FAQs. Total: {len(df)}")


if __name__ == "__main__":
    main()

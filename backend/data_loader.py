"""
Load FAQ data from Excel and manage ingestion change detection.

Pandas is imported only inside functions so the web server can start quickly
on Render before heavy data libraries load.
"""

import hashlib
import json
from pathlib import Path

from config import EMBEDDING_MODEL, EXCEL_PATH, INGESTION_META_PATH


def load_faqs_from_excel(excel_path: Path | None = None) -> list[dict[str, str]]:
    """Read Question/Answer pairs from hyundai_faq.xlsx."""
    import pandas as pd

    path = excel_path or EXCEL_PATH
    if not path.exists():
        raise FileNotFoundError(f"FAQ Excel file not found: {path}")

    df = pd.read_excel(path)

    if "Question" not in df.columns or "Answer" not in df.columns:
        raise ValueError("Excel must contain 'Question' and 'Answer' columns")

    faqs: list[dict[str, str]] = []
    for _, row in df.iterrows():
        question = str(row["Question"]).strip()
        answer = str(row["Answer"]).strip()
        if question and answer and question.lower() != "nan" and answer.lower() != "nan":
            faqs.append({"question": question, "answer": answer})

    if not faqs:
        raise ValueError("No valid FAQ entries found in Excel file")

    return faqs


def compute_excel_hash(excel_path: Path | None = None) -> str:
    """SHA-256 hash of Excel bytes — detects file edits."""
    path = excel_path or EXCEL_PATH
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_ingestion_meta() -> dict | None:
    if not INGESTION_META_PATH.exists():
        return None
    with open(INGESTION_META_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def write_ingestion_meta(meta: dict) -> None:
    INGESTION_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INGESTION_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def needs_reingestion(chroma_count: int, excel_faq_count: int) -> bool:
    if chroma_count == 0:
        return True

    meta = read_ingestion_meta()
    if meta is None:
        return True

    try:
        current_hash = compute_excel_hash()
    except FileNotFoundError:
        return True

    return (
        meta.get("excel_hash") != current_hash
        or meta.get("faq_count", 0) != excel_faq_count
        or chroma_count != excel_faq_count
        or meta.get("embedding_model") != EMBEDDING_MODEL
    )

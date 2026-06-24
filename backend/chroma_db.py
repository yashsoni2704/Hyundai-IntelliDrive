"""
ChromaDB integration for persistent semantic FAQ retrieval.

Architecture:
  - Each FAQ question = one vector document (atomic chunk, no text splitting)
  - Answer stored in metadata only (returned verbatim, never generated)
  - Search: embed query → top-12 cosine matches → filter by topic/vehicle → best match

ChromaDB uses HNSW index with cosine space: distance = 1 - cosine_similarity.
"""

import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chromadb
    from chromadb.api.models.Collection import Collection

from config import (
    CHROMA_PERSIST_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    EXCEL_PATH,
    SIMILARITY_THRESHOLD,
)
from data_loader import (
    load_faqs_from_excel,
    needs_reingestion,
    write_ingestion_meta,
    compute_excel_hash,
)
from context_service import VEHICLE_MODELS, detect_topic, detect_vehicle, normalize_message
from embeddings import embed_texts, embed_query

logger = logging.getLogger(__name__)

NO_DATA_MESSAGE = "Sorry, no data found."
SEARCH_STOPWORDS = {
    "a",
    "an",
    "are",
    "can",
    "car",
    "cars",
    "does",
    "hyundai",
    "i",
    "in",
    "is",
    "of",
    "the",
    "to",
    "what",
    "when",
    "which",
    "how",
    "many",
    "much",
    "this",
    "that",
    "with",
}

TOPIC_SIGNALS: dict[str, list[str]] = {
    "price": ["price", "cost", "lakh", "rupee", "starting"],
    "mileage": ["mileage", "kmpl", "km/l", "fuel efficiency", "fuel"],
    "seats": ["seat", "seater", "seating", "capacity"],
    "compare": ["compare", "comparison", "versus", " vs "],
    "features": ["feature", "specification", "spec"],
    "booking": ["test drive", "book", "booking", "slot", "schedule"],
    "service": ["warranty", "service"],
}


class FAQVectorStore:
    """
    Manages ChromaDB collection for Hyundai FAQ semantic search.

    Lifecycle:
      1. __init__ — connect to persistent ChromaDB folder
      2. initialize() — ingest Excel FAQs if needed
      3. search(query) — retrieve best matching stored answer
    """

    def __init__(self) -> None:
        import chromadb
        from chromadb.config import Settings

        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._initialized = False
        self._initializing = False
        self._init_error: str | None = None
        self._semantic_search_available = True

    @property
    def document_count(self) -> int:
        return self._collection.count()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_initializing(self) -> bool:
        return self._initializing

    @property
    def init_error(self) -> str | None:
        return self._init_error

    def initialize_safe(self) -> None:
        """
        Initialize KB without crashing the web server (for cloud deploys).
        On failure, sets init_error so /health can report the problem.
        """
        if self._initialized or self._initializing:
            return
        self._initializing = True
        self._init_error = None
        try:
            self.initialize()
        except Exception as exc:
            self._init_error = str(exc)
            logger.exception("Knowledge base initialization failed")
        finally:
            self._initializing = False

    def initialize(self) -> None:
        """
        Load FAQs into ChromaDB only when Excel changed or DB is empty.
        Ingestion: embed each QUESTION → store vector + answer in metadata.
        """
        logger.info("Initializing knowledge base from Excel...")
        faqs = load_faqs_from_excel()
        chroma_count = self.document_count
        excel_faq_count = len(faqs)

        logger.info("Loaded %d FAQs from Excel file", excel_faq_count)

        if not needs_reingestion(chroma_count, excel_faq_count):
            logger.info(
                "✓ ChromaDB up to date (%d documents). Skipping re-ingestion.",
                chroma_count,
            )
            self._initialized = True
            return

        logger.info("Re-ingesting %d FAQs into ChromaDB...", len(faqs))

        if chroma_count > 0:
            logger.info("Deleting old collection...")
            self._client.delete_collection(COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

        logger.info("Generating embeddings for %d FAQs (this may take a moment)...", len(faqs))
        questions = [faq["question"] for faq in faqs]
        answers = [faq["answer"] for faq in faqs]
        ids = [f"faq_{i}" for i in range(len(faqs))]
        embeddings = embed_texts(questions)
        logger.info("✓ Embeddings generated")

        logger.info("Adding documents to ChromaDB...")
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=questions,
            metadatas=[{"question": q, "answer": a} for q, a in zip(questions, answers)],
        )

        write_ingestion_meta(
            {
                "excel_hash": compute_excel_hash(),
                "faq_count": len(faqs),
                "embedding_model": EMBEDDING_MODEL,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("✓ Ingestion complete. %d documents stored.", self.document_count)
        self._initialized = True

    def _extract_vehicles(self, text: str) -> list[str]:
        normalized = normalize_message(text)
        lower = normalized.lower()
        found: list[str] = []
        for model in sorted(VEHICLE_MODELS, key=len, reverse=True):
            if model in lower:
                name = detect_vehicle(model)
                if name and name not in found:
                    found.append(name)
        v = detect_vehicle(normalized)
        if v and v not in found:
            found.append(v)
        return found

    def _topic_matches(self, topic: str, question: str, answer: str) -> bool:
        if not topic:
            return True
        blob = f"{question} {answer}".lower()
        signals = TOPIC_SIGNALS.get(topic, [])
        return any(sig in blob for sig in signals)

    def _vehicle_matches(
        self, vehicles: list[str], question: str, answer: str, query_topic: str
    ) -> bool:
        if not vehicles:
            return True
        blob = f"{question} {answer}".lower()
        if query_topic == "compare":
            return all(v.lower() in blob for v in vehicles)
        return any(v.lower() in blob for v in vehicles)

    def _pick_best_candidate(self, query: str, results: dict) -> dict | None:
        """
        Re-rank top ChromaDB hits using topic + vehicle filters.
        Prevents wrong answers (e.g. Creta price when user asked mileage).
        Score = 65% semantic similarity + 35% vehicle name overlap.
        """
        query_topic = detect_topic(query)
        query_vehicles = self._extract_vehicles(query)
        candidates: list[tuple[float, float, dict]] = []

        for i, dist in enumerate(results["distances"][0]):
            similarity = 1.0 - dist
            meta = results["metadatas"][0][i] or {}
            question = meta.get("question", results["documents"][0][i])
            answer = meta.get("answer", "")

            if not self._topic_matches(query_topic, question, answer):
                continue
            if not self._vehicle_matches(query_vehicles, question, answer, query_topic):
                continue

            vehicle_score = 0.5
            if query_vehicles:
                blob = question.lower()
                vehicle_score = sum(1 for v in query_vehicles if v.lower() in blob) / len(
                    query_vehicles
                )

            combined = (similarity * 0.65) + (vehicle_score * 0.35)
            candidates.append((combined, similarity, meta))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        _combined, best_sim, best_meta = candidates[0]
        if best_sim < SIMILARITY_THRESHOLD:
            return None
        return best_meta

    def search(self, query: str) -> dict:
        """
        Semantic similarity search — returns stored FAQ answer only (no LLM).

        Returns: {"answer": str, "found": bool}
        Falls back to keyword search if embedding model unavailable.
        """
        query = normalize_message(query.strip())
        if not query:
            return {"answer": NO_DATA_MESSAGE, "found": False}

        if self.document_count == 0:
            return {"answer": NO_DATA_MESSAGE, "found": False}

        if not self._semantic_search_available:
            return self._lexical_search(query)

        try:
            query_embedding = embed_query(query)
            n_results = min(12, self.document_count)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["metadatas", "distances", "documents"],
            )
        except Exception as exc:
            self._semantic_search_available = False
            logger.warning(
                "Semantic search unavailable (%s). Falling back to local keyword search.",
                exc,
            )
            return self._lexical_search(query)

        if not results["ids"] or not results["ids"][0]:
            return {"answer": NO_DATA_MESSAGE, "found": False}

        best_meta = self._pick_best_candidate(query, results)
        if not best_meta:
            return {"answer": NO_DATA_MESSAGE, "found": False}

        stored_answer = best_meta.get("answer", NO_DATA_MESSAGE)
        return {
            "answer": stored_answer,
            "found": True,
        }

    def _lexical_search(self, query: str) -> dict:
        """Fallback FAQ search when the embedding model is not available locally."""
        records = self._collection.get(include=["documents", "metadatas"])
        documents = records.get("documents") or []
        metadatas = records.get("metadatas") or []
        query_terms = {
            term
            for term in re.findall(r"[a-z0-9]+", query.lower())
            if term not in SEARCH_STOPWORDS
        }

        best_score = 0.0
        best_metadata = None
        query_topic = detect_topic(query)
        query_vehicles = self._extract_vehicles(query)

        for document, metadata in zip(documents, metadatas):
            question = (metadata or {}).get("question") or document or ""
            answer = (metadata or {}).get("answer") or ""
            question_lower = question.lower()

            if query_topic and not self._topic_matches(query_topic, question, answer):
                continue
            if not self._vehicle_matches(query_vehicles, question, answer, query_topic):
                continue

            question_terms = {
                term
                for term in re.findall(r"[a-z0-9]+", question_lower)
                if term not in SEARCH_STOPWORDS
            }
            if not question_terms:
                continue

            overlap = len(query_terms & question_terms) / max(len(query_terms), 1)
            phrase_bonus = 0.25 if query.lower() in question_lower or question_lower in query.lower() else 0.0
            similarity = SequenceMatcher(None, query.lower(), question_lower).ratio()
            score = (overlap * 0.65) + (similarity * 0.35) + phrase_bonus

            if score > best_score:
                best_score = score
                best_metadata = metadata

        if best_score < 0.22 or not best_metadata:
            return {
                "answer": NO_DATA_MESSAGE,
                "found": False,
                "similarity": round(best_score, 4),
                "search_mode": "keyword",
            }

        return {
            "answer": best_metadata.get("answer", NO_DATA_MESSAGE),
            "found": True,
            "similarity": round(min(best_score, 1.0), 4),
            "search_mode": "keyword",
        }

    def get_stats(self) -> dict:
        """Return knowledge base statistics for the dashboard panel."""
        faqs = load_faqs_from_excel()
        return {
            "total_faqs_loaded": len(faqs),
            "chroma_document_count": self.document_count,
            "embedding_model": EMBEDDING_MODEL,
            "chroma_status": "initialized" if self.is_initialized else "initializing",
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "excel_path": str(EXCEL_PATH),
        }


_store: FAQVectorStore | None = None


def get_vector_store() -> FAQVectorStore:
    """Lazy singleton — avoids heavy Chroma init during uvicorn import."""
    global _store
    if _store is None:
        _store = FAQVectorStore()
    return _store


class _VectorStoreProxy:
    """Defer FAQVectorStore() until first attribute access (after port bind)."""

    def __getattr__(self, name: str):
        return getattr(get_vector_store(), name)


# Imported by app.py — proxy only, no heavy work at import time
vector_store = _VectorStoreProxy()

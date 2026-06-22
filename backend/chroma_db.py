"""ChromaDB integration for persistent semantic FAQ retrieval."""

import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

import chromadb
from chromadb.config import Settings

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
}


class FAQVectorStore:
    """Manages ChromaDB collection for Hyundai FAQ semantic search."""

    def __init__(self) -> None:
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
        self._semantic_search_available = True

    @property
    def document_count(self) -> int:
        return self._collection.count()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def initialize(self) -> None:
        """Load FAQs into ChromaDB only when needed."""
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

    def search(self, query: str) -> dict:
        """
        Perform semantic similarity search and return stored answer only.

        Returns dict with keys: answer, found, similarity (optional).
        """
        query = query.strip()
        if not query:
            return {"answer": NO_DATA_MESSAGE, "found": False}

        if self.document_count == 0:
            return {"answer": NO_DATA_MESSAGE, "found": False}

        if not self._semantic_search_available:
            return self._lexical_search(query)

        try:
            query_embedding = embed_query(query)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=1,
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

        distance = results["distances"][0][0]
        # Cosine distance in Chroma: 0 = identical, 2 = opposite
        similarity = 1.0 - distance

        if similarity < SIMILARITY_THRESHOLD:
            return {
                "answer": NO_DATA_MESSAGE,
                "found": False,
                "similarity": round(similarity, 4),
            }

        metadata = results["metadatas"][0][0]
        stored_answer = metadata.get("answer", NO_DATA_MESSAGE)

        return {
            "answer": stored_answer,
            "found": True,
            "similarity": round(similarity, 4),
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

        for document, metadata in zip(documents, metadatas):
            question = (metadata or {}).get("question") or document or ""
            question_lower = question.lower()
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


# Singleton instance used by the API
vector_store = FAQVectorStore()

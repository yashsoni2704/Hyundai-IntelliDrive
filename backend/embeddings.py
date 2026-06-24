"""
Local embedding generation using BGE-M3 (sentence-transformers).

An embedding is a list of numbers (1024 floats) representing the MEANING of text.
Similar questions produce similar vectors, enabling semantic search.

We embed FAQ QUESTIONS at ingestion time and user QUERIES at search time.
Answers are NOT embedded — they are stored in ChromaDB metadata and returned as-is.
"""

import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load BGE-M3 once and cache it in memory.
    @lru_cache ensures the heavy model download/load happens only on first call.
    First run may take 2-5 minutes while Hugging Face downloads ~2GB.
    """
    logger.info("Loading embedding model: %s (first run may take 2-5 minutes)...", EMBEDDING_MODEL)
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("✓ Embedding model loaded successfully")
        return model
    except Exception as exc:
        logger.error("Failed to load embedding model: %s", exc)
        raise


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert a list of strings into embedding vectors.
    normalize_embeddings=True → unit vectors so cosine similarity = dot product.
    Used during FAQ ingestion (batch embed all questions).
    """
    model = get_embedding_model()
    logger.debug("Generating embeddings for %d texts", len(texts))
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()  # convert numpy array to plain Python list for ChromaDB


def embed_query(query: str) -> list[float]:
    """Embed a single user query at search time."""
    return embed_texts([query])[0]

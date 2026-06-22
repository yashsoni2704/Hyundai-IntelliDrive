"""Local embedding generation using BGE-M3 (sentence-transformers, no LLM)."""

import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load and cache the BGE-M3 embedding model."""
    logger.info("Loading embedding model: %s (first run may take 2-5 minutes)...", EMBEDDING_MODEL)
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("✓ Embedding model loaded successfully")
        return model
    except Exception as exc:
        logger.error("Failed to load embedding model: %s", exc)
        raise


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate normalized embeddings for a list of texts."""
    model = get_embedding_model()
    logger.debug("Generating embeddings for %d texts", len(texts))
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Generate embedding for a single user query."""
    return embed_texts([query])[0]

"""
Local embedding generation using BGE-M3 / MiniLM (sentence-transformers).

IMPORTANT for cloud deploy: SentenceTransformer is imported LAZILY inside
get_embedding_model() so uvicorn can bind to $PORT before PyTorch loads.
"""

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from config import EMBEDDING_MODEL

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> "SentenceTransformer":
    """Load and cache the embedding model (first call downloads weights)."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s (first run may take a few minutes)...", EMBEDDING_MODEL)
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
        return model
    except Exception as exc:
        logger.error("Failed to load embedding model: %s", exc)
        raise


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert text list to normalized embedding vectors."""
    model = get_embedding_model()
    logger.debug("Generating embeddings for %d texts", len(texts))
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single user query at search time."""
    return embed_texts([query])[0]

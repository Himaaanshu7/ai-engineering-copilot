"""
Local embedding model via sentence-transformers.
Loaded once and reused — downloading ~90 MB on first run.
"""

from functools import lru_cache

from loguru import logger

from config.settings import settings


@lru_cache(maxsize=1)
def get_embedder():
    """Return a cached SentenceTransformer instance."""
    from sentence_transformers import SentenceTransformer
    logger.info(f"[Embedder] Loading model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)
    logger.info("[Embedder] Model ready")
    return model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings. Returns a list of float vectors."""
    model = get_embedder()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]

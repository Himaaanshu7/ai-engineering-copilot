"""
ChromaDB persistent vector store.

Single collection named by settings.chroma_collection_name.
All operations are synchronous (ChromaDB has no async client).
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger

from config.settings import settings


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    persist_dir = str(Path(settings.chroma_persist_dir).resolve())
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"[ChromaDB] Connecting | persist_dir={persist_dir}")
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client


def get_collection(name: str | None = None) -> chromadb.Collection:
    client = get_chroma_client()
    col_name = name or settings.chroma_collection_name
    collection = client.get_or_create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def add_documents(
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
    collection_name: str | None = None,
) -> None:
    from rag.embedder import embed_texts

    collection = get_collection(collection_name)
    embeddings = embed_texts(texts)
    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info(f"[ChromaDB] Added {len(texts)} chunks to '{collection.name}'")


def query_documents(
    query: str,
    n_results: int = 5,
    where: Optional[dict] = None,
    collection_name: str | None = None,
) -> list[dict]:
    """
    Semantic search. Returns list of dicts with keys:
      id, document, metadata, distance
    """
    from rag.embedder import embed_query

    collection = get_collection(collection_name)
    count = collection.count()
    if count == 0:
        logger.debug("[ChromaDB] Collection empty — no results")
        return []

    n = min(n_results, count)
    kwargs: dict = {"query_embeddings": [embed_query(query)], "n_results": n, "include": ["documents", "metadatas", "distances"]}
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    output: list[dict] = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return output


def collection_stats(collection_name: str | None = None) -> dict:
    collection = get_collection(collection_name)
    return {"name": collection.name, "count": collection.count()}


def delete_by_source(source: str, collection_name: str | None = None) -> int:
    """Delete all chunks from a given source document."""
    collection = get_collection(collection_name)
    results = collection.get(where={"source": source})
    ids = results["ids"]
    if ids:
        collection.delete(ids=ids)
        logger.info(f"[ChromaDB] Deleted {len(ids)} chunks from source='{source}'")
    return len(ids)

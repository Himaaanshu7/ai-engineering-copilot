"""
Document ingestion pipeline.

Splits text into overlapping chunks, embeds them, and stores in ChromaDB.
Supports: .txt, .md, .py, .sql, .csv (header only), .pdf (via PyMuPDF)
"""

import hashlib
import re
from pathlib import Path
from typing import Optional

from loguru import logger


# ── Chunking ───────────────────────────────────────────────────────────────────

def _split_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[str]:
    """Split text into overlapping chunks on sentence/paragraph boundaries."""
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text.strip())

    # Try to split on double newlines (paragraphs) first
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # If single paragraph is too long, hard-split it
            if len(para) > chunk_size:
                words = para.split()
                buf = ""
                for word in words:
                    if len(buf) + len(word) + 1 <= chunk_size:
                        buf = (buf + " " + word).strip()
                    else:
                        if buf:
                            chunks.append(buf)
                        buf = word
                if buf:
                    current = buf
            else:
                current = para

    if current:
        chunks.append(current)

    # Apply overlap: prepend the tail of the previous chunk
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-chunk_overlap:]
            overlapped.append((tail + " " + chunks[i]).strip())
        return overlapped

    return chunks


def _read_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            return "\n\n".join(page.get_text() for page in doc)
        except ImportError:
            logger.warning("[Ingestion] PyMuPDF not available — skipping PDF")
            return ""
    else:
        return path.read_text(encoding="utf-8", errors="ignore")


def _make_chunk_id(source: str, index: int, text: str) -> str:
    digest = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{source}::{index}::{digest}"


# ── Public API ─────────────────────────────────────────────────────────────────

def ingest_text(
    text: str,
    source: str,
    extra_metadata: Optional[dict] = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    collection_name: str | None = None,
) -> int:
    """
    Chunk and ingest a raw text string into ChromaDB.

    Args:
        text:       Raw text content.
        source:     Logical name for this document (used for dedup / deletion).
        extra_metadata: Additional metadata fields to store per chunk.
        collection_name: Override the default collection.

    Returns:
        Number of chunks ingested.
    """
    from rag.vectorstore import add_documents, delete_by_source

    # Remove stale chunks from this source
    delete_by_source(source, collection_name)

    chunks = _split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        logger.warning(f"[Ingestion] No chunks from source='{source}'")
        return 0

    metadatas = [
        {"source": source, "chunk_index": i, **(extra_metadata or {})}
        for i, _ in enumerate(chunks)
    ]
    ids = [_make_chunk_id(source, i, chunk) for i, chunk in enumerate(chunks)]

    add_documents(texts=chunks, metadatas=metadatas, ids=ids, collection_name=collection_name)
    logger.info(f"[Ingestion] Ingested {len(chunks)} chunks | source='{source}'")
    return len(chunks)


def ingest_file(
    file_path: str | Path,
    source_name: str | None = None,
    collection_name: str | None = None,
) -> int:
    """
    Read a file and ingest its contents.

    Args:
        file_path:    Absolute path to the file.
        source_name:  Override the source label (defaults to filename).

    Returns:
        Number of chunks ingested.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"[Ingestion] File not found: {path}")
        return 0

    source = source_name or path.name
    text = _read_file(path)
    if not text.strip():
        logger.warning(f"[Ingestion] Empty content for: {path}")
        return 0

    return ingest_text(
        text=text,
        source=source,
        extra_metadata={"file_path": str(path), "file_type": path.suffix.lstrip(".")},
        collection_name=collection_name,
    )


def ingest_directory(
    dir_path: str | Path,
    extensions: tuple[str, ...] = (".txt", ".md", ".py", ".sql"),
    collection_name: str | None = None,
) -> dict[str, int]:
    """
    Ingest all supported files in a directory recursively.

    Returns:
        Dict mapping filename → chunk count.
    """
    dir_path = Path(dir_path)
    results: dict[str, int] = {}

    for path in sorted(dir_path.rglob("*")):
        if path.suffix.lower() in extensions and path.is_file():
            count = ingest_file(path, collection_name=collection_name)
            results[path.name] = count

    total = sum(results.values())
    logger.info(f"[Ingestion] Directory done | files={len(results)} | total_chunks={total}")
    return results

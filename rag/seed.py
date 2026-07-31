"""
Seed the ChromaDB knowledge base with curated technical documentation.
Run once: python -m rag.seed
Re-running is safe — existing chunks for each source are deleted before re-ingestion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from rag.ingestion import ingest_directory, ingest_file
from rag.vectorstore import collection_stats


def seed() -> None:
    docs_dir = Path(__file__).parent.parent / "data" / "docs"
    if not docs_dir.exists():
        logger.error(f"Docs directory not found: {docs_dir}")
        return

    md_files = list(docs_dir.glob("*.md"))
    txt_files = list(docs_dir.glob("*.txt"))
    all_files = md_files + txt_files

    if not all_files:
        logger.warning(f"No .md or .txt files in {docs_dir}")
        return

    logger.info(f"Seeding knowledge base | {len(all_files)} documents")
    total = 0
    for path in sorted(all_files):
        count = ingest_file(path)
        logger.info(f"  {path.name} → {count} chunks")
        total += count

    stats = collection_stats()
    logger.info(f"Seed complete | total_chunks={total} | collection_size={stats['count']}")


if __name__ == "__main__":
    seed()

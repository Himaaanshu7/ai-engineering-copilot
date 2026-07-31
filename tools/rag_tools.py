"""
RAG tools for the Research Agent.

Tools:
  - search_knowledge_base: semantic search over ingested docs
  - ingest_uploaded_file:  add an uploaded file to the vector store
"""

from pathlib import Path

from langchain_core.tools import tool
from loguru import logger


@tool
def search_knowledge_base(query: str, n_results: int = 5) -> str:
    """Search the internal knowledge base for relevant technical documentation.

    Covers: LangGraph, RAG pipelines, Apache Spark, dbt, SQL, Python patterns,
    data engineering best practices, and any files the user has uploaded.

    Call this before answering technical questions to retrieve grounding context.

    Args:
        query:     The search query — phrase it as a question or key terms.
        n_results: Number of chunks to retrieve (default 5, max 10).

    Returns:
        Formatted context passages with source labels, or a message if nothing found.
    """
    try:
        from rag.vectorstore import query_documents, collection_stats

        stats = collection_stats()
        if stats["count"] == 0:
            return "Knowledge base is empty. Answering from model training knowledge only."

        n = min(max(1, n_results), 10)
        results = query_documents(query, n_results=n)

        if not results:
            return "No relevant documents found in the knowledge base for this query."

        # Filter out low-relevance results (cosine distance > 0.6 = not very similar)
        relevant = [r for r in results if r["distance"] < 0.6]
        if not relevant:
            relevant = results[:2]  # fallback: return top 2 anyway

        lines: list[str] = [f"**Retrieved {len(relevant)} relevant chunks:**\n"]
        for i, r in enumerate(relevant, 1):
            source = r["metadata"].get("source", "unknown")
            chunk_idx = r["metadata"].get("chunk_index", "?")
            score = round(1 - r["distance"], 3)
            lines.append(f"**[{i}] Source: {source} (chunk {chunk_idx}, relevance {score})**")
            lines.append(r["document"][:600])  # cap chunk length in prompt
            lines.append("")

        return "\n".join(lines)

    except Exception as exc:
        logger.warning(f"[RAG Tool] search_knowledge_base error: {exc}")
        return f"Knowledge base search unavailable: {exc}"


@tool
def ingest_uploaded_file(file_path: str) -> str:
    """Add a file from the uploads directory into the knowledge base for future searches.

    Supports: .txt, .md, .py, .sql, .pdf

    Args:
        file_path: Absolute path to the uploaded file.

    Returns:
        Confirmation with chunk count, or error message.
    """
    try:
        from rag.ingestion import ingest_file

        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"

        allowed = {".txt", ".md", ".py", ".sql", ".pdf", ".csv"}
        if path.suffix.lower() not in allowed:
            return f"File type '{path.suffix}' not supported for ingestion."

        count = ingest_file(path)
        return f"Successfully ingested '{path.name}' into the knowledge base ({count} chunks created)."

    except Exception as exc:
        logger.warning(f"[RAG Tool] ingest_uploaded_file error: {exc}")
        return f"Ingestion failed: {exc}"

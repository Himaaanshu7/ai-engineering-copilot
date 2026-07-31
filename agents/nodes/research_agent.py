"""
Research Agent — Phase 9

Two-stage context retrieval before calling the LLM:
  Stage 1: ChromaDB semantic search (local, always available)
  Stage 2: Tavily web search (if KB context is weak OR web search is explicitly needed)

The LLM receives both KB chunks and live web results injected into the system prompt.
No tool-calling is used for retrieval — one LLM call generates the final response.

Quality gate: if the best KB result has cosine distance >= 0.55 (weak match), web search
is triggered automatically. This ensures fresh/obscure topics still get good answers.
"""

from loguru import logger

from agents.graph.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage
from llm.factory import LLMFactory

# Cosine distance threshold above which we also trigger web search
_KB_WEAK_THRESHOLD = 0.55

_BASE_PROMPT = """You are a Principal Data & AI Engineer with experience at top-tier tech companies.
You have access to a curated knowledge base and live web search results.

Your expertise:
- **Data Engineering**: Apache Spark, Airflow, dbt, Kafka, Flink, Delta Lake, Apache Iceberg
- **Cloud Platforms**: AWS, GCP, Azure — data and ML services
- **AI/ML Engineering**: LangChain, LangGraph, RAG, vector databases, LLMs, MLOps
- **Databases**: PostgreSQL, DuckDB, Snowflake, Databricks, ChromaDB, Pinecone
- **System Design**: distributed systems, event-driven architecture, microservices

{context_block}

Response format:
1. **What it is** — 1-2 sentence clear definition
2. **How it works** — mechanism and key components
3. **When to use it** — concrete use cases
4. **When NOT to use it** — tradeoffs and alternatives
5. **Example** — code snippet or architecture description
6. **Sources** — cite which documents or URLs informed the answer

For comparisons: side-by-side table + concrete recommendation.
Be opinionated and direct. Prioritize retrieved context over generic knowledge."""


# ── Stage 1: ChromaDB retrieval ────────────────────────────────────────────────

def _retrieve_from_kb(query: str, n_results: int = 5) -> tuple[str, list[str], float]:
    """
    Returns (formatted_context, source_names, best_distance).
    best_distance = 0.0 means perfect match; 1.0 means no match.
    """
    try:
        from rag.vectorstore import query_documents, collection_stats

        if collection_stats()["count"] == 0:
            return "", [], 1.0

        results = query_documents(query, n_results=n_results)
        if not results:
            return "", [], 1.0

        best_distance = results[0]["distance"]
        relevant = [r for r in results if r["distance"] < 0.65]
        if not relevant:
            return "", [], best_distance

        lines: list[str] = ["**Knowledge base context:**\n"]
        sources: list[str] = []
        for i, r in enumerate(relevant, 1):
            source = r["metadata"].get("source", "unknown")
            score = round(1 - r["distance"], 3)
            lines.append(f"[KB {i} | {source} | relevance {score}]")
            lines.append(r["document"][:700])
            lines.append("")
            if source not in sources:
                sources.append(source)

        return "\n".join(lines), sources, best_distance

    except Exception as exc:
        logger.warning(f"[Research Agent] KB retrieval failed: {exc}")
        return "", [], 1.0


# ── Stage 2: Tavily web search ────────────────────────────────────────────────

def _retrieve_from_web(query: str, max_results: int = 4) -> tuple[str, list[str]]:
    """
    Returns (formatted_context, source_urls).
    Returns empty strings if Tavily is not configured.
    """
    try:
        from tools.web_search_tools import search_technical_docs, format_search_results, is_search_available

        if not is_search_available():
            logger.debug("[Research Agent] Tavily not configured — skipping web search")
            return "", []

        results = search_technical_docs(query, max_results=max_results)
        if not results:
            return "", []

        formatted = format_search_results(results, max_chars_per_result=350)
        urls = [r.get("url", "") for r in results if r.get("url")]
        return formatted, urls

    except Exception as exc:
        logger.warning(f"[Research Agent] Web search failed: {exc}")
        return "", []


# ── Agent node ─────────────────────────────────────────────────────────────────

async def research_agent_node(state: AgentState) -> dict:
    query = state["user_input"]
    logger.info(f"[Research Agent] Processing | input={query[:60]}...")

    # Stage 1: KB retrieval
    kb_context, kb_sources, best_distance = _retrieve_from_kb(query)

    if kb_context:
        logger.info(f"[Research Agent] KB hit | sources={kb_sources} | best_dist={best_distance:.3f}")
    else:
        logger.debug("[Research Agent] KB miss")

    # Stage 2: Web search — trigger if KB is weak or empty
    web_context, web_urls = "", []
    if best_distance >= _KB_WEAK_THRESHOLD:
        logger.info("[Research Agent] KB context weak — triggering web search")
        web_context, web_urls = _retrieve_from_web(query)
        if web_context:
            logger.info(f"[Research Agent] Web results retrieved | urls={len(web_urls)}")

    # Build context block
    context_parts: list[str] = []
    if kb_context:
        context_parts.append(kb_context)
    if web_context:
        context_parts.append(web_context)

    if context_parts:
        context_block = (
            "**Use the following retrieved context to ground your response. "
            "Cite the sources in your answer.**\n\n"
            + "\n\n---\n\n".join(context_parts)
        )
    else:
        context_block = (
            "No specific documentation was retrieved. "
            "Answer from expert engineering knowledge."
        )

    # Single LLM call with injected context
    system_prompt = _BASE_PROMPT.format(context_block=context_block)
    llm = LLMFactory.get_llm(temperature=0.1)

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=query),
    ])

    # Combine all sources
    all_sources = list(dict.fromkeys(kb_sources + web_urls))

    logger.info(f"[Research Agent] Done | kb_sources={len(kb_sources)} | web_urls={len(web_urls)}")
    return {
        "research_result": response.content,
        "final_response": response.content,
        "rag_context": [kb_context] if kb_context else [],
        "sources": all_sources,
    }

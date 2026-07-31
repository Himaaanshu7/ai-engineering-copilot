"""
Web search tools powered by Tavily.

Degrades gracefully when TAVILY_API_KEY is not set:
  - search_web returns an explanatory message
  - fetch_page_content still works (no API key needed for direct fetch)

Tavily free tier: 1,000 searches/month — https://app.tavily.com
"""

from loguru import logger

from config.settings import settings


def _get_tavily_client():
    """Return a TavilyClient or raise if not configured."""
    if not settings.tavily_api_key or settings.tavily_api_key.startswith("your_"):
        raise ValueError("TAVILY_API_KEY not configured. Add it to .env to enable web search.")
    from tavily import TavilyClient
    return TavilyClient(api_key=settings.tavily_api_key)


def search_web(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_domains: list[str] | None = None,
) -> list[dict]:
    """
    Search the web via Tavily. Returns list of result dicts with keys:
      title, url, content (snippet), score

    Args:
        query:           The search query.
        max_results:     Number of results (1-10).
        search_depth:    "basic" (fast) or "advanced" (deeper, uses more credits).
        include_domains: Optional whitelist of domains to search within.

    Returns:
        List of result dicts, or empty list on failure/unavailable.
    """
    try:
        client = _get_tavily_client()
        kwargs: dict = {
            "query": query,
            "max_results": min(max_results, 10),
            "search_depth": search_depth,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains

        response = client.search(**kwargs)
        results = response.get("results", [])
        logger.info(f"[Tavily] Search complete | query={query[:60]!r} | results={len(results)}")
        return results

    except ValueError as exc:
        logger.warning(f"[Tavily] Not configured: {exc}")
        return []
    except Exception as exc:
        logger.warning(f"[Tavily] Search failed: {exc}")
        return []


def search_technical_docs(query: str, max_results: int = 5) -> list[dict]:
    """
    Search restricted to high-quality technical documentation sites.
    Focuses on official docs, GitHub, Stack Overflow, and major tech blogs.
    """
    tech_domains = [
        "docs.python.org",
        "spark.apache.org",
        "docs.getdbt.com",
        "langchain.com",
        "python.langchain.com",
        "github.com",
        "stackoverflow.com",
        "medium.com",
        "towardsdatascience.com",
        "databricks.com",
        "docs.snowflake.com",
        "docs.aws.amazon.com",
        "cloud.google.com",
    ]
    return search_web(query, max_results=max_results, include_domains=tech_domains)


def format_search_results(results: list[dict], max_chars_per_result: int = 400) -> str:
    """Format Tavily results into a string suitable for LLM context injection."""
    if not results:
        return ""

    lines: list[str] = [f"**Web search results ({len(results)} sources):**\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        content = r.get("content", "")[:max_chars_per_result]
        score = round(r.get("score", 0), 3)
        lines.append(f"**[{i}] {title}** (relevance: {score})")
        lines.append(f"URL: {url}")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def is_search_available() -> bool:
    """Return True if Tavily is configured and ready."""
    try:
        _get_tavily_client()
        return True
    except ValueError:
        return False

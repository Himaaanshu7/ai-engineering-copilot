"""
SQL Agent — Phase 6

Capabilities:
  • Expert SQL advice (all queries — no file needed)
  • Anti-pattern detection via analyze_sql_quality tool
  • DuckDB execution against uploaded CSV/Parquet (when file_path is in state)
  • Schema profiling so the LLM knows column names before writing queries

Architecture: single LangGraph node with an internal agentic loop (max 3 iterations).
The node binds tools to the LLM, runs tool calls, feeds results back, and produces a
final natural-language response.
"""

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from loguru import logger

from agents.graph.state import AgentState
from llm.factory import LLMFactory
from tools.sql_tools import analyze_sql_quality, make_file_tools

_SQL_SYSTEM_PROMPT = """You are a Senior SQL Engineer and Database Architect with deep expertise \
across PostgreSQL, MySQL, BigQuery, Snowflake, Redshift, DuckDB, Databricks SQL, and Spark SQL.

Your expertise covers:
- Query optimization and execution plan analysis (EXPLAIN / EXPLAIN ANALYZE)
- Index strategy: B-tree, hash, partial, composite, covering, and GIN indexes
- Window functions, CTEs, recursive queries, lateral joins, PIVOT/UNPIVOT
- Anti-pattern detection: N+1 queries, implicit conversions, correlated subqueries, SELECT *, cartesian products
- Partitioning, clustering, materialized views, and query pruning
- Data modeling: 3NF, star schema, snowflake schema, data vault
- FAANG-level SQL interview questions

Tool usage guidelines:
1. If the user provides SQL to analyze or optimize → call analyze_sql_quality first
2. If a data file is available → call profile_data_file first to learn the schema, then write and run queries
3. Never guess column names — always profile the file before querying it
4. Use execute_sql_on_data only after you know the schema

Response format for SQL problems:
1. **Problem identified** — what is wrong or being asked
2. **Solution** — optimized query in a ```sql block
3. **Why this is better** — execution plan reasoning, index usage
4. **Additional suggestions** — schema changes, indexes if relevant

Always use ```sql code blocks. Be direct and technical."""

_MAX_TOOL_ITERATIONS = 5


async def sql_agent_node(state: AgentState) -> dict:
    file_path: str | None = state.get("uploaded_file_path")
    has_file = file_path is not None and Path(file_path).exists()

    logger.info(f"[SQL Agent] Processing | file={'yes' if has_file else 'no'} | input={state['user_input'][:60]}...")

    # Build tool list
    tools = [analyze_sql_quality]
    if has_file:
        tools.extend(make_file_tools(file_path))
        logger.info(f"[SQL Agent] File tools enabled | path={file_path}")

    llm = LLMFactory.get_llm(temperature=0.05)
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}

    # Add file context hint to user input when a file is available
    user_content = state["user_input"]
    if has_file:
        fname = Path(file_path).name
        user_content = f"[Uploaded file: {fname}]\n\n{user_content}"

    messages: list = [
        SystemMessage(content=_SQL_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    final_response = ""

    for iteration in range(_MAX_TOOL_ITERATIONS):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not getattr(response, "tool_calls", None):
            final_response = response.content
            logger.info(f"[SQL Agent] Done | iterations={iteration + 1}")
            break

        # Execute each tool call and feed results back
        for tc in response.tool_calls:
            tool_fn = tool_map.get(tc["name"])
            if tool_fn is None:
                tool_result = f"Unknown tool: {tc['name']}"
            else:
                logger.debug(f"[SQL Agent] Tool call: {tc['name']} args={list(tc['args'].keys())}")
                tool_result = tool_fn.invoke(tc["args"])

            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))
    else:
        # Max iterations hit — use last non-tool-call content or summarize
        final_response = response.content or "Reached tool iteration limit. Please ask a more specific question."

    logger.info("[SQL Agent] Response ready")
    return {
        "sql_result": final_response,
        "final_response": final_response,
    }

"""
Python Agent — Phase 7

Capabilities:
  • Expert Python advice for any question (no code required)
  • AST structural analysis via analyze_python_code
  • Anti-pattern detection via detect_python_issues
  • Cyclomatic complexity + maintainability index via calculate_complexity
  • Sandboxed execution to verify fixes via execute_python_snippet

Architecture: same internal agentic loop as the SQL agent (max 3 iterations).
"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from loguru import logger

from agents.graph.state import AgentState
from llm.factory import LLMFactory
from tools.python_tools import (
    analyze_python_code,
    calculate_complexity,
    detect_python_issues,
    execute_python_snippet,
)

_PYTHON_SYSTEM_PROMPT = """You are a Senior Python Engineer with deep expertise in Python 3.10+, \
data engineering, AI/ML pipelines, async patterns, and clean code architecture.

Your expertise covers:
- Debugging: tracebacks, memory leaks, race conditions, off-by-one errors, type errors
- Refactoring: readability, SOLID principles, DRY, design patterns (factory, strategy, decorator)
- Performance: Big-O complexity, profiling, generators vs lists, vectorization, Cython hints
- Data engineering: Pandas, Polars, PySpark, NumPy — idiomatic patterns and common pitfalls
- Async Python: asyncio event loop, async/await, aiohttp, FastAPI dependency injection
- Type system: type hints, Pydantic, dataclasses, TypeVar, Protocol, overload
- Testing: pytest fixtures, parametrize, monkeypatch, async tests
- Modern Python: walrus operator, structural pattern matching, positional-only args

Tool usage guidelines:
1. If the user provides Python code → call analyze_python_code first to understand the structure
2. Then call detect_python_issues to catch anti-patterns
3. If the code has functions → call calculate_complexity to assess quality
4. After producing a fix → call execute_python_snippet to verify the corrected code works
5. Do NOT execute code with file I/O, network calls, or long loops

Response format:
1. **Root cause** — precise diagnosis of the problem
2. **Fixed code** — complete, runnable solution in a ```python block
3. **Why** — clear explanation of what changed and why
4. **Complexity** — time/space if relevant
5. **Further improvements** — optional but valuable suggestions

Never use placeholder comments. Write the actual implementation."""

_MAX_TOOL_ITERATIONS = 5
_ALL_TOOLS = [analyze_python_code, detect_python_issues, calculate_complexity, execute_python_snippet]


async def python_agent_node(state: AgentState) -> dict:
    logger.info(f"[Python Agent] Processing | input={state['user_input'][:60]}...")

    llm = LLMFactory.get_llm(temperature=0.05)
    llm_with_tools = llm.bind_tools(_ALL_TOOLS)
    tool_map = {t.name: t for t in _ALL_TOOLS}

    messages: list = [
        SystemMessage(content=_PYTHON_SYSTEM_PROMPT),
        HumanMessage(content=state["user_input"]),
    ]

    final_response = ""

    for iteration in range(_MAX_TOOL_ITERATIONS):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not getattr(response, "tool_calls", None):
            final_response = response.content
            logger.info(f"[Python Agent] Done | iterations={iteration + 1}")
            break

        for tc in response.tool_calls:
            tool_fn = tool_map.get(tc["name"])
            if tool_fn is None:
                tool_result = f"Unknown tool: {tc['name']}"
            else:
                logger.debug(f"[Python Agent] Tool call: {tc['name']}")
                tool_result = tool_fn.invoke(tc["args"])

            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))
    else:
        final_response = response.content or "Reached tool iteration limit. Please ask a more specific question."

    logger.info("[Python Agent] Response ready")
    return {
        "python_result": final_response,
        "final_response": final_response,
    }

"""
Phase 2 sanity tests.
Run: pytest tests/unit/test_phase2.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from config.settings import settings
from llm.factory import LLMFactory
from agents.graph.state import AgentState
from agents.graph.graph import create_graph


def test_settings_load():
    assert settings.app_name == "AI Engineering Copilot"
    assert settings.llm_provider in ("groq", "openai", "claude", "ollama")


def test_llm_factory_groq():
    """LLMFactory should return a ChatGroq instance without raising."""
    if not settings.groq_api_key:
        pytest.skip("GROQ_API_KEY not set")
    llm = LLMFactory.get_llm("groq")
    assert llm is not None


def test_graph_compiles():
    """LangGraph should compile without errors."""
    graph = create_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_graph_invoke():
    """End-to-end: graph should return a non-empty response via Groq."""
    if not settings.groq_api_key:
        pytest.skip("GROQ_API_KEY not set")

    graph = create_graph()
    result = await graph.ainvoke({
        "messages": [],
        "user_input": "What is Apache Spark?",
        "session_id": "test-session",
        "intent": "",
        "active_agents": [],
        "sql_result": None,
        "python_result": None,
        "research_result": None,
        "rag_context": None,
        "github_result": None,
        "report": None,
        "sources": [],
        "final_response": "",
        "error": None,
    })

    assert result["final_response"] != ""
    assert result["intent"] != ""
    print(f"\nIntent: {result['intent']}")
    print(f"Response preview: {result['final_response'][:200]}")

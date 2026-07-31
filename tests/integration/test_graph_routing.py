"""Integration tests for LangGraph routing and agent dispatch."""
import pytest
from config.settings import settings
from agents.graph.graph import create_graph
from agents.graph.router import route_by_intent


def _base_state(user_input: str, intent: str = "") -> dict:
    return {
        "messages": [],
        "user_input": user_input,
        "session_id": "integration-test",
        "intent": intent,
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
        "uploaded_file_path": None,
    }


def test_graph_compiles():
    graph = create_graph()
    assert graph is not None


def test_route_by_intent_sql():
    state = _base_state("Write a SQL query", intent="sql")
    assert route_by_intent(state) == "sql_agent"


def test_route_by_intent_python():
    state = _base_state("Debug my Python code", intent="python")
    assert route_by_intent(state) == "python_agent"


def test_route_by_intent_research():
    state = _base_state("Explain Apache Spark", intent="research")
    assert route_by_intent(state) == "research_agent"


def test_route_by_intent_github():
    state = _base_state("Analyze this repo", intent="github")
    assert route_by_intent(state) == "github_agent"


def test_route_by_intent_interview():
    state = _base_state("Give me interview questions", intent="interview")
    assert route_by_intent(state) == "interview_agent"


def test_route_by_intent_general_fallback():
    state = _base_state("Hello!", intent="general")
    assert route_by_intent(state) == "general_agent"


def test_route_by_intent_unknown_falls_back():
    state = _base_state("Hello!", intent="unknown_intent_xyz")
    assert route_by_intent(state) == "general_agent"


@pytest.mark.asyncio
async def test_graph_invoke_sql():
    """Live test: graph should route SQL questions to sql_agent."""
    if not settings.groq_api_key:
        pytest.skip("GROQ_API_KEY not set")

    graph = create_graph()
    result = await graph.ainvoke(_base_state("Write a SQL SELECT query to count rows in a table"))

    assert result["final_response"] != ""
    assert result["intent"] in ("sql", "general")


@pytest.mark.asyncio
async def test_graph_invoke_python():
    """Live test: graph should route Python questions to python_agent."""
    if not settings.groq_api_key:
        pytest.skip("GROQ_API_KEY not set")

    graph = create_graph()
    result = await graph.ainvoke(_base_state("What is wrong with: def f(x=[]): x.append(1); return x"))

    assert result["final_response"] != ""
    assert result["intent"] in ("python", "general")

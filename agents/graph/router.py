from agents.graph.state import AgentState


_INTENT_TO_NODE: dict[str, str] = {
    "sql": "sql_agent",
    "python": "python_agent",
    "research": "research_agent",
    "github": "github_agent",
    # data_analysis routes to research_agent until Phase 8 adds the dedicated data agent
    "data_analysis": "research_agent",
    "interview": "interview_agent",
    "general": "general_agent",
}


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "general")
    return _INTENT_TO_NODE.get(intent, "general_agent")

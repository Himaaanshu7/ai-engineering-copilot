from langgraph.graph import END, StateGraph
from loguru import logger

from agents.graph.state import AgentState
from agents.graph.router import route_by_intent, _INTENT_TO_NODE
from agents.nodes.planner import planner_node
from agents.nodes.sql_agent import sql_agent_node
from agents.nodes.python_agent import python_agent_node
from agents.nodes.research_agent import research_agent_node
from agents.nodes.github_agent import github_agent_node
from agents.nodes.interview_agent import interview_agent_node
from agents.nodes.general_agent import general_agent_node

_AGENT_NODES = {
    "sql_agent": sql_agent_node,
    "python_agent": python_agent_node,
    "research_agent": research_agent_node,
    "github_agent": github_agent_node,
    "interview_agent": interview_agent_node,
    "general_agent": general_agent_node,
}


def create_graph():
    """
    Phase 5 graph: Planner classifies intent → router → specialized agent node.

    Topology:
        START → planner → [route_by_intent] → {sql_agent | python_agent |
        research_agent | github_agent | interview_agent | general_agent} → END
    """
    builder = StateGraph(AgentState)

    builder.add_node("planner", planner_node)
    for name, fn in _AGENT_NODES.items():
        builder.add_node(name, fn)

    builder.set_entry_point("planner")

    # Conditional routing from planner based on classified intent
    builder.add_conditional_edges(
        "planner",
        route_by_intent,
        {node: node for node in _AGENT_NODES},
    )

    for node in _AGENT_NODES:
        builder.add_edge(node, END)

    graph = builder.compile()
    node_list = ["planner"] + list(_AGENT_NODES.keys())
    logger.info(f"LangGraph compiled | nodes={node_list} | phase=5")
    return graph

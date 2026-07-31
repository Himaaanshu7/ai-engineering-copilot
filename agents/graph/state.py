from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Shared state that flows through every node in the LangGraph.

    Each agent reads from and writes to this state. The Planner sets
    'intent' and 'active_agents'; specialized agents populate their
    respective result fields; the synthesizer reads all results to
    produce 'final_response'.
    """

    # Conversation history — append-only via add_messages reducer
    messages: Annotated[list, add_messages]

    # Core request context
    user_input: str
    session_id: str
    uploaded_file_path: Optional[str]  # absolute path to an uploaded file (set by chat route)

    # Planner outputs
    intent: str
    active_agents: list[str]

    # Specialized agent outputs (None until that agent runs)
    sql_result: Optional[str]
    python_result: Optional[str]
    research_result: Optional[str]
    rag_context: Optional[list[str]]
    github_result: Optional[str]
    report: Optional[str]

    # Accumulated source citations
    sources: list[str]

    # Final synthesized response
    final_response: str

    # Error propagation
    error: Optional[str]

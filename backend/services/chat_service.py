from agents.graph.graph import create_graph
from loguru import logger

# Compile once at import time — reused across all requests
_graph = create_graph()


async def process_chat(user_input: str, session_id: str, file_path: str | None = None) -> dict:
    """Run the LangGraph pipeline and return the final state dict."""
    initial_state = {
        "messages": [],
        "user_input": user_input,
        "session_id": session_id,
        "uploaded_file_path": file_path,
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
    }
    logger.debug(f"[ChatService] Invoking graph | session={session_id[:8]}")
    return await _graph.ainvoke(initial_state)

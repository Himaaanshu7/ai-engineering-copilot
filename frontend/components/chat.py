import streamlit as st

from frontend.utils.api_client import APIClient
from frontend.utils.formatters import build_file_context
from frontend.utils.export import messages_to_markdown


_INTENT_COLORS: dict[str, str] = {
    "sql": "blue",
    "python": "green",
    "research": "violet",
    "github": "orange",
    "data_analysis": "blue",
    "interview": "orange",
    "general": "gray",
    "error": "red",
}

_INTENT_ICONS: dict[str, str] = {
    "sql": ":material/database:",
    "python": ":material/code:",
    "research": ":material/search:",
    "github": ":material/hub:",
    "data_analysis": ":material/table_chart:",
    "interview": ":material/quiz:",
    "general": ":material/lightbulb:",
    "error": ":material/error:",
}

_INTENT_LABELS: dict[str, str] = {
    "sql": "SQL",
    "python": "Python",
    "research": "Research",
    "github": "GitHub",
    "data_analysis": "Data analysis",
    "interview": "Interview prep",
    "general": "General",
    "error": "Error",
}

# Suggestion cards shown on the welcome screen
_SUGGESTION_CARDS = [
    {
        "icon": ":material/database:",
        "title": "SQL optimization",
        "desc": "Query tuning, indexes, anti-patterns, execution plans",
        "prompt": (
            "Optimize this SQL query and explain every change you make:\n\n"
            "```sql\nSELECT *\nFROM orders o\nJOIN customers c ON o.customer_id = c.id\n"
            "WHERE o.status = 'pending'\nORDER BY o.created_at DESC\n```"
        ),
    },
    {
        "icon": ":material/code:",
        "title": "Python debugging",
        "desc": "Bug detection, refactoring, complexity, best practices",
        "prompt": (
            "Debug this Python code, identify the root cause, and fix it:\n\n"
            "```python\ndef fibonacci(n):\n    return fibonacci(n-1) + fibonacci(n-2)\n\n"
            "print(fibonacci(10))\n```"
        ),
    },
    {
        "icon": ":material/hub:",
        "title": "LangGraph explained",
        "desc": "Multi-agent orchestration, state graphs, routing",
        "prompt": (
            "Explain LangGraph in depth: what it is, how it differs from basic LangChain agents, "
            "the StateGraph concept, and when I should use it. Include a practical example."
        ),
    },
    {
        "icon": ":material/quiz:",
        "title": "Databricks interview",
        "desc": "Senior-level questions on Delta Lake, Spark, Unity Catalog",
        "prompt": (
            "Give me 5 senior-level Databricks interview questions with detailed answers. "
            "Cover Delta Lake ACID transactions, Spark optimization, and Unity Catalog."
        ),
    },
    {
        "icon": ":material/search:",
        "title": "RAG architecture",
        "desc": "Chunking, embeddings, vector stores, production patterns",
        "prompt": (
            "Explain RAG (Retrieval-Augmented Generation) architecture in depth: "
            "chunking strategies, embedding models, vector stores, retrieval ranking, "
            "and production best practices."
        ),
    },
    {
        "icon": ":material/table_chart:",
        "title": "Data modeling",
        "desc": "Star schema, Data Vault, OBT — when to use each",
        "prompt": (
            "Compare star schema vs. Data Vault vs. one big table (OBT) for a modern Lakehouse. "
            "When should I choose each approach? Include trade-offs."
        ),
    },
]

_ACCEPTED_FILE_TYPES = ["py", "sql", "txt", "md", "csv", "json", "yaml", "yml", "pdf", "parquet"]


def _render_message(msg: dict) -> None:
    """Render a stored message with metadata."""
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            intent = msg.get("intent", "general")
            icon = _INTENT_ICONS.get(intent, ":material/lightbulb:")
            color = _INTENT_COLORS.get(intent, "gray")
            agent = msg.get("agent_used", "planner")

            col_badge, col_meta = st.columns([1, 5])
            with col_badge:
                label = _INTENT_LABELS.get(intent, intent.title())
                st.badge(label, icon=icon, color=color)
            with col_meta:
                st.caption(f"Agent: `{agent}`")

            sources = msg.get("sources") or []
            if sources:
                with st.expander(":material/link: Sources", expanded=False):
                    for src in sources:
                        st.markdown(f"- {src}")

        if msg.get("file_name"):
            st.caption(f":material/attach_file: `{msg['file_name']}`")


def _call_backend(
    api: APIClient,
    full_message: str,
    display_content: str,
    file_names: list[str],
) -> None:
    """Send message to backend, render response, persist both to session state."""

    # ── User bubble ───────────────────────────────────────────────────────────
    st.session_state.messages.append({
        "role": "user",
        "content": display_content,
        "file_name": file_names[0] if file_names else None,
    })
    with st.chat_message("user"):
        st.markdown(display_content)

    # ── Assistant bubble ──────────────────────────────────────────────────────
    with st.chat_message("assistant"):
        if not st.session_state.get("backend_ok", False):
            st.error(
                "Backend is offline. Start the FastAPI server first.",
                icon=":material/error:",
            )
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Backend is offline.",
                "intent": "error",
                "agent_used": "—",
                "sources": [],
            })
            return

        with st.status(":material/smart_toy: Processing…", expanded=False) as status:
            result = api.send_message(
                message=full_message,
                session_id=st.session_state.session_id,
            )
            if "error" in result:
                status.update(label="Error", state="error")
            else:
                status.update(label="Done", state="complete")

        if "error" in result:
            st.error(result["error"], icon=":material/error:")
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["error"],
                "intent": "error",
                "agent_used": "—",
                "sources": [],
            })
            return

        response_text = result.get("response", "No response received.")
        intent = result.get("intent", "general")
        agent = result.get("agent_used", "planner")
        sources = result.get("sources") or []

        st.markdown(response_text)

        col_badge, col_meta = st.columns([1, 5])
        with col_badge:
            icon = _INTENT_ICONS.get(intent, ":material/lightbulb:")
            color = _INTENT_COLORS.get(intent, "gray")
            label = _INTENT_LABELS.get(intent, intent.title())
            st.badge(label, icon=icon, color=color)
        with col_meta:
            st.caption(f"Agent: `{agent}`")

        if sources:
            with st.expander(":material/link: Sources", expanded=False):
                for src in sources:
                    st.markdown(f"- {src}")

        if file_names:
            st.caption(f":material/attach_file: `{'`, `'.join(file_names)}`")

        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "intent": intent,
            "agent_used": agent,
            "sources": sources,
            "file_name": file_names[0] if file_names else None,
        })

        if file_names:
            st.session_state.uploaded_files.extend(file_names)


def _render_welcome() -> None:
    """Hero section + suggestion card grid shown when no messages exist."""

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.space("large")
    with st.container(horizontal_alignment="center"):
        st.markdown("# :material/engineering: AI Engineering Copilot")
        st.markdown(
            ":gray[Expert AI mentor for **SQL · Python · Spark · dbt · Airflow · "
            "LangGraph · RAG · System Design · Interviews**]"
        )
    st.space("large")

    # ── Suggestion cards — 3-column grid ─────────────────────────────────────
    st.markdown("**Start exploring**")
    st.space("small")

    cols = st.columns(3)
    for i, card in enumerate(_SUGGESTION_CARDS):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"#### {card['icon']}")
                st.markdown(f"**{card['title']}**")
                st.caption(card["desc"])
                st.space("small")
                if st.button(
                    "Try this",
                    key=f"suggestion_card_{i}",
                    type="primary",
                    icon=":material/arrow_forward:",
                ):
                    st.session_state.pending_prompt = card["prompt"]
                    st.rerun()

    st.space("large")


def render_chat(api: APIClient) -> None:
    session_id: str = st.session_state.session_id

    # ── Process pending prompt (from suggestion cards) ─────────────────────────
    pending: str | None = st.session_state.get("pending_prompt")
    if pending:
        st.session_state.pending_prompt = None
        _call_backend(api, pending, pending, [])
        st.rerun()
        return

    # ── Welcome screen ────────────────────────────────────────────────────────
    if not st.session_state.messages:
        _render_welcome()

    # ── Message history ────────────────────────────────────────────────────────
    for msg in st.session_state.messages:
        _render_message(msg)

    # ── Export button ─────────────────────────────────────────────────────────
    if st.session_state.messages:
        export_md = messages_to_markdown(st.session_state.messages, session_id)
        with st.container(horizontal_alignment="right"):
            st.download_button(
                label="Export",
                icon=":material/download:",
                data=export_md,
                file_name=f"copilot-{session_id[:8]}.md",
                mime="text/markdown",
                help="Download this conversation as Markdown",
            )

    # ── Chat input ─────────────────────────────────────────────────────────────
    prompt = st.chat_input(
        "Ask about SQL, Python, Spark, dbt, LangGraph, system design…",
        accept_file="multiple",
        file_type=_ACCEPTED_FILE_TYPES,
        submit_mode="stop",
    )

    if not prompt:
        return

    user_text: str = prompt.text if hasattr(prompt, "text") else str(prompt)
    raw_files = getattr(prompt, "files", None) or []

    file_context_parts: list[str] = []
    file_names: list[str] = []
    for f in raw_files:
        ctx, fname = build_file_context(f)
        file_context_parts.append(ctx)
        file_names.append(fname)

    full_message = "\n\n".join(filter(None, file_context_parts + [user_text])).strip()
    if not full_message:
        st.warning("Please type a message or attach a file.", icon=":material/warning:")
        return

    if file_names and user_text:
        display_content = f":material/attach_file: `{'`, `'.join(file_names)}`\n\n{user_text}"
    elif file_names:
        display_content = f":material/attach_file: `{'`, `'.join(file_names)}` — analyze this file."
    else:
        display_content = user_text

    _call_backend(api, full_message, display_content, file_names)
    st.rerun()

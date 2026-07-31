import streamlit as st

from frontend.utils.export import messages_to_markdown


def render_history() -> None:
    st.markdown("## :material/history: Session history")

    messages: list[dict] = st.session_state.get("messages", [])

    if not messages:
        with st.container(border=True):
            col_icon, col_text = st.columns([1, 6])
            with col_icon:
                st.markdown(":material/forum:")
            with col_text:
                st.markdown("**No messages yet**")
                st.caption("Start a conversation on the Chat tab — it will appear here.")
        return

    # ── Stats row ─────────────────────────────────────────────────────────────
    user_msgs = [m for m in messages if m["role"] == "user"]
    asst_msgs = [m for m in messages if m["role"] == "assistant"]

    intent_counts: dict[str, int] = {}
    for m in asst_msgs:
        intent = m.get("intent") or "general"
        if intent != "error":
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

    files_analyzed = len({m["file_name"] for m in messages if m.get("file_name")})
    top_intent = (
        max(intent_counts, key=lambda k: intent_counts[k]) if intent_counts else "—"
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.metric("Exchanges", len(user_msgs))
    with col2:
        with st.container(border=True):
            st.metric("Top intent", top_intent)
    with col3:
        with st.container(border=True):
            st.metric("Files analyzed", files_analyzed)
    with col4:
        with st.container(border=True):
            unique_agents = len({m.get("agent_used", "planner") for m in asst_msgs})
            st.metric("Agents used", unique_agents)

    st.space("medium")

    # ── Actions row ───────────────────────────────────────────────────────────
    export_md = messages_to_markdown(messages, st.session_state.session_id)
    col_dl, col_intent = st.columns([1, 2])
    with col_dl:
        st.download_button(
            label="Download as Markdown",
            icon=":material/download:",
            data=export_md,
            file_name=f"copilot-{st.session_state.session_id[:8]}.md",
            mime="text/markdown",
        )

    with col_intent:
        if intent_counts:
            with st.expander(":material/analytics: Intent breakdown"):
                for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
                    pct = round(count / len(user_msgs) * 100) if user_msgs else 0
                    st.caption(f"`{intent}` — {count} exchange{'s' if count > 1 else ''} ({pct}%)")

    st.space("medium")

    # ── Conversation timeline ──────────────────────────────────────────────────
    st.markdown("### Conversation timeline")

    for msg in messages:
        if msg["role"] == "user":
            role_label = "You"
            icon = ":material/person:"
        else:
            role_label = "Copilot"
            icon = ":material/smart_toy:"

        intent = msg.get("intent", "")
        intent_tag = (
            f" · `{intent}`"
            if intent and msg["role"] == "assistant" and intent not in ("error", "")
            else ""
        )
        file_tag = f" · :material/attach_file: `{msg['file_name']}`" if msg.get("file_name") else ""

        preview = msg["content"].replace("\n", " ")[:72]
        if len(msg["content"]) > 72:
            preview += "…"

        with st.expander(
            f"{role_label}{intent_tag}{file_tag} — {preview}",
            expanded=False,
            icon=icon,
        ):
            st.markdown(msg["content"])
            sources = msg.get("sources") or []
            if sources:
                st.markdown("**Sources:**")
                for src in sources:
                    st.markdown(f"- {src}")

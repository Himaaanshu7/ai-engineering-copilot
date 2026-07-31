import streamlit as st

from frontend.utils.export import messages_to_markdown
from frontend.utils.api_client import get_api_client


def _get_client():
    return get_api_client()


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

    # ── Export / Report row ───────────────────────────────────────────────────
    st.markdown("### :material/download: Export")

    export_md = messages_to_markdown(messages, st.session_state.session_id)

    col_md, col_pdf, col_intent = st.columns([1, 1, 2])

    with col_md:
        st.download_button(
            label="Download Markdown",
            icon=":material/description:",
            data=export_md,
            file_name=f"copilot-{st.session_state.session_id[:8]}.md",
            mime="text/markdown",
        )

    with col_pdf:
        if st.button(":material/picture_as_pdf: Download PDF", key="btn_pdf"):
            with st.spinner("Generating PDF…"):
                try:
                    client = _get_client()
                    pdf_bytes = client.generate_pdf(
                        messages=messages,
                        session_id=st.session_state.session_id,
                    )
                    if pdf_bytes:
                        st.session_state["_pdf_bytes"] = pdf_bytes
                        st.rerun()
                except Exception as exc:
                    st.error(f"PDF generation failed: {exc}")

    # Show download button once PDF is ready
    if "_pdf_bytes" in st.session_state:
        st.download_button(
            label="Click to save PDF",
            icon=":material/save:",
            data=st.session_state["_pdf_bytes"],
            file_name=f"copilot-{st.session_state.session_id[:8]}.pdf",
            mime="application/pdf",
            key="btn_save_pdf",
        )

    with col_intent:
        if intent_counts:
            with st.expander(":material/analytics: Intent breakdown"):
                for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
                    pct = round(count / len(user_msgs) * 100) if user_msgs else 0
                    st.caption(f"`{intent}` — {count} exchange{'s' if count > 1 else ''} ({pct}%)")

    st.space("medium")

    # ── AI Report Generator ───────────────────────────────────────────────────
    st.markdown("### :material/auto_awesome: AI Report Generator")
    st.caption("Let the AI write a structured report from your session — choose the style below.")

    report_type = st.segmented_control(
        "Report type",
        options=["summary", "technical", "interview"],
        format_func=lambda x: {"summary": "Session Summary", "technical": "Technical Deep-Dive", "interview": "Interview Prep Sheet"}[x],
        default="summary",
        key="report_type_select",
        label_visibility="collapsed",
    )

    if st.button(":material/auto_awesome: Generate Report", key="btn_generate_report", type="primary"):
        with st.spinner(f"Writing {report_type} report…"):
            try:
                client = _get_client()
                result = client.generate_report(
                    messages=messages,
                    session_id=st.session_state.session_id,
                    report_type=report_type,
                )
                if result:
                    st.session_state["_generated_report"] = result
                    st.session_state["_generated_report_type"] = report_type
                    st.rerun()
            except Exception as exc:
                st.error(f"Report generation failed: {exc}")

    if "_generated_report" in st.session_state:
        report_md = st.session_state["_generated_report"]
        rtype = st.session_state.get("_generated_report_type", "summary")

        st.success(f"{rtype.title()} report ready!")

        col_view, col_dl = st.columns([3, 1])
        with col_view:
            with st.expander(":material/article: View report", expanded=True):
                st.markdown(report_md)
        with col_dl:
            st.download_button(
                label="Download report",
                icon=":material/download:",
                data=report_md,
                file_name=f"copilot-report-{rtype}-{st.session_state.session_id[:8]}.md",
                mime="text/markdown",
                key="btn_dl_report",
            )

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

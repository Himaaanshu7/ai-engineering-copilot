import streamlit as st

from frontend.utils.api_client import APIClient
from frontend.utils.formatters import build_file_context


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

_ACCEPTED_EXTENSIONS = [
    "py", "sql", "txt", "md", "csv", "json", "yaml", "yml", "parquet", "pdf",
]

_DEFAULT_QUESTIONS: dict[str, str] = {
    "py": "Review this Python code. Identify bugs, performance issues, and suggest improvements with explanations.",
    "sql": "Analyze this SQL query. Identify anti-patterns, optimize it, and explain the changes.",
    "csv": "Profile this dataset. Describe the columns, flag data quality issues, and suggest analysis approaches.",
    "parquet": "Profile this dataset. Describe the schema, column statistics, and suggest analysis approaches.",
    "json": "Analyze this JSON structure. Describe its schema and suggest any improvements.",
    "md": "Review this Markdown document for clarity, structure, and completeness.",
    "txt": "Analyze this text file and provide insights.",
    "yaml": "Review this YAML configuration file for correctness and best practices.",
    "yml": "Review this YAML configuration file for correctness and best practices.",
    "pdf": "Describe what you'd like to know about this PDF document.",
}

_FILE_TYPE_INFO = {
    "py": ("Python script", ":material/code:", "green"),
    "sql": ("SQL query", ":material/database:", "blue"),
    "csv": ("CSV dataset", ":material/table_chart:", "blue"),
    "parquet": ("Parquet dataset", ":material/table_chart:", "blue"),
    "json": ("JSON file", ":material/data_object:", "orange"),
    "yaml": ("YAML config", ":material/settings:", "violet"),
    "yml": ("YAML config", ":material/settings:", "violet"),
    "md": ("Markdown doc", ":material/description:", "gray"),
    "txt": ("Text file", ":material/text_snippet:", "gray"),
    "pdf": ("PDF document", ":material/picture_as_pdf:", "red"),
}


def _preview_file(uploaded, ext: str) -> None:
    lang_map = {
        "py": "python", "sql": "sql", "json": "json",
        "yaml": "yaml", "yml": "yaml", "txt": "text", "md": "markdown",
    }

    if ext in lang_map:
        content = uploaded.read().decode("utf-8", errors="replace")
        uploaded.seek(0)
        with st.expander(":material/visibility: File preview", expanded=True):
            st.code(content[:3000], language=lang_map[ext])
            if len(content) > 3000:
                st.caption(f"*(Showing first 3,000 of {len(content):,} characters)*")

    elif ext == "csv":
        try:
            import pandas as pd
            df = pd.read_csv(uploaded)
            uploaded.seek(0)
            with st.expander(":material/table_chart: Data preview", expanded=True):
                col_r, col_c, col_null = st.columns(3)
                col_r.metric("Rows", f"{df.shape[0]:,}")
                col_c.metric("Columns", df.shape[1])
                col_null.metric("Null values", int(df.isnull().sum().sum()))
                st.dataframe(df.head(50))
                with st.expander(":material/info: Column types"):
                    dtype_df = df.dtypes.reset_index()
                    dtype_df.columns = ["column", "dtype"]
                    st.dataframe(dtype_df)
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}", icon=":material/error:")

    elif ext == "parquet":
        try:
            import pandas as pd
            df = pd.read_parquet(uploaded)
            uploaded.seek(0)
            with st.expander(":material/table_chart: Data preview", expanded=True):
                col_r, col_c = st.columns(2)
                col_r.metric("Rows", f"{df.shape[0]:,}")
                col_c.metric("Columns", df.shape[1])
                st.dataframe(df.head(50))
        except Exception as exc:
            st.error(f"Could not read Parquet: {exc}", icon=":material/error:")

    elif ext == "pdf":
        st.info(
            "Full PDF parsing (PyMuPDF + RAG) arrives in Phase 8. "
            "Describe what you'd like to know in the question below.",
            icon=":material/info:",
        )


def render_file_analysis(api: APIClient) -> None:
    st.markdown("## :material/description: File analysis")
    st.caption("Upload a file — the copilot reads it and provides expert analysis.")

    st.space("small")

    uploaded = st.file_uploader(
        "Upload a file",
        type=_ACCEPTED_EXTENSIONS,
        label_visibility="collapsed",
        help="Supported: .py · .sql · .csv · .parquet · .json · .yaml · .md · .txt · .pdf",
    )

    # ── Empty state ───────────────────────────────────────────────────────────
    if not uploaded:
        with st.container(border=True):
            col_icon, col_text = st.columns([1, 5])
            with col_icon:
                st.markdown(":material/upload_file:", help=None)
            with col_text:
                st.markdown("**Drag and drop a file here, or click Browse**")
                st.caption(
                    "`.py` · `.sql` · `.csv` · `.parquet` · `.json` · `.yaml` · `.md` · `.txt` · `.pdf`"
                )
        return

    ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
    type_label, type_icon, type_color = _FILE_TYPE_INFO.get(ext, ("File", ":material/description:", "gray"))

    # ── File header ───────────────────────────────────────────────────────────
    col_name, col_badge = st.columns([4, 1])
    with col_name:
        st.markdown(f"### :material/attach_file: `{uploaded.name}`")
    with col_badge:
        st.badge(type_label, icon=type_icon, color=type_color)

    # ── Preview ───────────────────────────────────────────────────────────────
    _preview_file(uploaded, ext)

    st.space("medium")

    # ── Question ──────────────────────────────────────────────────────────────
    default_q = _DEFAULT_QUESTIONS.get(ext, "Analyze this file and provide insights.")
    question = st.text_area(
        "What would you like to know?",
        value=default_q,
        height=100,
        key="file_analysis_question",
    )

    if not st.button("Analyze", icon=":material/send:", type="primary"):
        return

    # ── Run ───────────────────────────────────────────────────────────────────
    if not st.session_state.get("backend_ok", False):
        st.error("Backend is offline. Start the FastAPI server first.", icon=":material/error:")
        return

    uploaded.seek(0)
    file_context, fname = build_file_context(uploaded)
    full_message = f"{file_context}\n\n{question}".strip()

    with st.status(":material/smart_toy: Analyzing with LangGraph…", expanded=True) as status:
        result = api.send_message(
            message=full_message,
            session_id=st.session_state.session_id,
        )
        if "error" in result:
            status.update(label="Error", state="error")
        else:
            status.update(label="Analysis complete", state="complete")

    st.space("small")

    if "error" in result:
        st.error(result["error"], icon=":material/error:")
        return

    response_text = result.get("response", "")
    intent = result.get("intent", "general")
    agent = result.get("agent_used", "planner")
    sources = result.get("sources") or []

    st.markdown("### :material/lightbulb: Analysis")

    with st.container(border=True):
        st.markdown(response_text)

    col_badge, col_meta = st.columns([1, 5])
    with col_badge:
        icon = _INTENT_ICONS.get(intent, ":material/lightbulb:")
        color = _INTENT_COLORS.get(intent, "gray")
        st.badge(intent, icon=icon, color=color)
    with col_meta:
        st.caption(f"Agent: `{agent}`")

    if sources:
        with st.expander(":material/link: Sources"):
            for src in sources:
                st.markdown(f"- {src}")

    # Persist to chat history for continuity
    st.session_state.messages.append({
        "role": "user",
        "content": f":material/attach_file: `{fname}` — {question}",
        "file_name": fname,
    })
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "intent": intent,
        "agent_used": agent,
        "sources": sources,
        "file_name": fname,
    })

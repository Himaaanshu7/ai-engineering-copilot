import uuid
import streamlit as st
from frontend.utils.api_client import APIClient


def render_sidebar(api: APIClient, app_version: str) -> None:
    with st.sidebar:
        # ── Brand ────────────────────────────────────────────────────────────
        st.markdown("## :material/engineering: Copilot")
        st.caption("AI mentor for data & AI engineering")

        st.space("medium")

        # ── Backend status ────────────────────────────────────────────────────
        health = api.health_check()
        with st.container(border=True):
            if health.get("status") == "ok":
                st.session_state.backend_ok = True
                provider = health.get("llm_provider", "").upper()
                model = health.get("llm_model", "")
                col_dot, col_info = st.columns([1, 6])
                with col_dot:
                    st.markdown(":green[●]")
                with col_info:
                    st.markdown(f"**Online** · {provider}")
                st.caption(f":material/smart_toy: `{model}`")
            else:
                st.session_state.backend_ok = False
                col_dot, col_info = st.columns([1, 6])
                with col_dot:
                    st.markdown(":red[●]")
                with col_info:
                    st.markdown("**Offline**")
                st.caption("Run: `uvicorn backend.main:app --reload`")

            st.caption(f":material/tag: `{st.session_state.session_id[:8]}…`")

        st.space("medium")

        # ── Capabilities ──────────────────────────────────────────────────────
        st.caption("CAPABILITIES")
        st.markdown(
            ":blue-badge[SQL] "
            ":green-badge[Python] "
            ":violet-badge[RAG] "
            ":orange-badge[GitHub] "
            ":blue-badge[CSV / Parquet] "
            ":orange-badge[Spark] "
            ":green-badge[dbt] "
            ":violet-badge[LangGraph] "
            ":red-badge[Interviews] "
            ":gray-badge[System design]"
        )

        st.space("large")

        # ── Session actions ───────────────────────────────────────────────────
        st.caption("SESSION")
        col_clear, col_new = st.columns(2)
        with col_clear:
            if st.button(
                "Clear",
                icon=":material/delete:",
                type="secondary",
                help="Clear all messages in this conversation",
            ):
                st.session_state.messages = []
                st.session_state.uploaded_files = []
                st.rerun()
        with col_new:
            if st.button(
                "New",
                icon=":material/add:",
                type="secondary",
                help="Start a fresh session with a new ID",
            ):
                st.session_state.messages = []
                st.session_state.uploaded_files = []
                st.session_state.session_id = str(uuid.uuid4())
                st.rerun()

        # ── Message count ─────────────────────────────────────────────────────
        msg_count = len([m for m in st.session_state.get("messages", []) if m["role"] == "user"])
        if msg_count > 0:
            st.space("small")
            plural = "s" if msg_count != 1 else ""
            st.caption(f":material/forum: {msg_count} message{plural} this session")

        st.space("large")

        # ── Version footer ────────────────────────────────────────────────────
        st.caption(f"v{app_version} · :material/hub: LangGraph · :material/code: Groq")

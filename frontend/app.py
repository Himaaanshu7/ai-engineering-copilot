import sys
from pathlib import Path

# Project root on path so all modules resolve correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
import streamlit as st

from config.settings import settings
from frontend.utils.api_client import get_api_client
from frontend.components.sidebar import render_sidebar
from frontend.components.chat import render_chat
from frontend.components.file_analysis import render_file_analysis
from frontend.components.history import render_history

# ── Page config — must be first Streamlit call ──────────────────────────────────
st.set_page_config(
    page_title="AI Engineering Copilot",
    page_icon=":material/engineering:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Product polish — remove Streamlit chrome ─────────────────────────────────
st.html("""
<style>
#MainMenu { visibility: hidden !important; }
footer { visibility: hidden !important; }
[data-testid="stDeployButton"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; }

/* Slim custom scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(97,175,239,0.25); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(97,175,239,0.55); }

/* Tab active highlight */
[data-baseweb="tab-highlight"] { background-color: #61afef !important; }

/* Tighten sidebar top padding */
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem !important; }

/* Soften chat message background edge */
[data-testid="stChatMessage"] { border-radius: 8px; }
</style>
""")

# ── Session state — initialise once per session ─────────────────────────────────
st.session_state.setdefault("session_id", str(uuid.uuid4()))
st.session_state.setdefault("messages", [])
st.session_state.setdefault("uploaded_files", [])
st.session_state.setdefault("backend_ok", False)
st.session_state.setdefault("pending_prompt", None)

# ── Shared API client (cached per server process) ───────────────────────────────
api = get_api_client(settings.backend_url)

# ── Sidebar ──────────────────────────────────────────────────────────────────────
render_sidebar(api, settings.app_version)

# ── Main content ─────────────────────────────────────────────────────────────────
tab_chat, tab_files, tab_history = st.tabs([
    ":material/chat: Chat",
    ":material/description: File analysis",
    ":material/history: Session history",
])

with tab_chat:
    render_chat(api)

with tab_files:
    render_file_analysis(api)

with tab_history:
    render_history()

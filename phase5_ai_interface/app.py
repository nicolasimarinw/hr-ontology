"""Streamlit app: HR Ontology AI Query Interface (multipage entry point)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

# Page config -- only allowed in the entry point
st.set_page_config(
    page_title="HR Ontology - AI Query Interface",
    page_icon=":office:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Shared session state initialization ---
if "agent" not in st.session_state:
    st.session_state.agent = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "tool_calls" not in st.session_state:
    st.session_state.tool_calls = []
if "latest_viz" not in st.session_state:
    st.session_state.latest_viz = None

# --- Sidebar branding + API key (shared across all pages) ---
with st.sidebar:
    st.title("HR Ontology")
    st.caption("AI-Powered HR Analytics")

    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=st.session_state.get("api_key", ""),
        help="Enter your Anthropic API key to enable the AI assistant.",
    )
    if api_key:
        st.session_state.api_key = api_key

    st.divider()
    st.caption("Meridian Technologies")
    st.caption("750 employees \u00b7 5 divisions \u00b7 20 departments")


# --- Welcome page ---
st.header("HR Ontology Explorer")
st.markdown(
    """
    Welcome to the **Meridian Technologies HR Ontology** interface.

    Use the sidebar to navigate between pages:

    - **Dashboard** -- KPI metrics, AI chat assistant, and graph visualizations
    - **Employee Explorer** -- Drill into any employee's ontological data, relationships, and interactive ego-graph
    """
)

col1, col2, col3 = st.columns(3)
col1.info("**750** Employees")
col2.info("**22** Node Types")
col3.info("**29** Relationship Types")

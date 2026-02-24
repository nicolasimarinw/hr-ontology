"""Dashboard page: KPI bar, AI chat, and visualization panel."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import streamlit as st

from config.settings import EXPORTS_DIR
from phase5_ai_interface.claude_agent import HRAgent
from phase5_ai_interface.tools.cypher_tools import query_graph
from phase5_ai_interface.tools.duckdb_tools import query_data_lake


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

HR_AREA_KEYWORDS = {
    "Recruiting": ["recruit", "hiring", "candidate", "requisition", "source", "applicant"],
    "Performance": ["performance", "rating", "review", "appraisal", "goal"],
    "Compensation": ["salary", "pay", "compensation", "equity", "bonus", "wage"],
    "Skills": ["skill", "competenc", "certification", "training", "learning"],
    "Org Structure": ["org chart", "span of control", "hierarchy", "reports to", "manager"],
    "Flight Risk": ["flight risk", "attrition", "turnover", "retention", "leaving"],
    "Diversity": ["diversity", "gender", "equity", "inclusion", "demographic"],
}

_TAG_BADGE_CSS = """
<style>
/* Pill badges inside expander labels */
div[data-testid="stExpander"] summary span code {
    background: #374151;
    color: #d1d5db;
    border-radius: 9999px;
    padding: 1px 8px;
    font-size: 0.72em;
    font-weight: 500;
    margin-left: 4px;
    white-space: nowrap;
}
</style>
"""


def _extract_summary(response: str) -> str:
    """Return the first meaningful line of a response, truncated to ~120 chars."""
    for line in response.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if len(stripped) > 10:
            return stripped[:120] + ("..." if len(stripped) > 120 else "")
    return response[:120] + ("..." if len(response) > 120 else "")


def _extract_tags(response: str, tool_log: list) -> list[str]:
    """Extract employee IDs, department names, and HR area tags."""
    tags = []

    # Employee IDs
    emp_ids = list(dict.fromkeys(re.findall(r"EMP-\d{5}", response)))
    tags.extend(emp_ids[:3])

    # Department names from tool results
    departments = set()
    for tc in tool_log:
        result_str = tc.get("result", "")
        try:
            parsed = json.loads(result_str)
            for row in parsed.get("rows", []):
                for key in ("department", "dept", "department_name", "name"):
                    val = row.get(key)
                    if val and isinstance(val, str) and len(val) < 40:
                        departments.add(val)
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
    tags.extend(sorted(departments)[:2])

    # HR area keyword matching
    lower_resp = response.lower()
    for area, keywords in HR_AREA_KEYWORDS.items():
        if any(kw in lower_resp for kw in keywords):
            tags.append(area)

    # Cap at 6 total, deduplicate
    seen = set()
    unique = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique.append(t)
        if len(unique) >= 6:
            break
    return unique


def _render_collapsed_pair(user_msg: dict, assistant_msg: dict, index: int):
    """Render a single Q&A pair as a collapsed expander card."""
    query = assistant_msg.get("query", user_msg.get("content", "Question"))
    tags = assistant_msg.get("tags", [])
    summary = assistant_msg.get("summary", "")

    # Build label: truncated question + tag badges
    label_question = query[:80] + ("..." if len(query) > 80 else "")
    badge_str = " ".join(f"`{t}`" for t in tags) if tags else ""
    label = f"{label_question}  {badge_str}" if badge_str else label_question

    with st.expander(label, expanded=False):
        if summary:
            st.caption(summary)
        st.markdown(assistant_msg.get("content", ""))
        tool_calls = assistant_msg.get("tool_calls", [])
        if tool_calls:
            with st.expander(f"Tool calls ({len(tool_calls)})", expanded=False):
                for tc in tool_calls:
                    st.code(
                        f"Tool: {tc['tool']}\n"
                        f"Input: {json.dumps(tc['input'], indent=2)}\n"
                        f"Result preview: {tc['result'][:500]}...",
                        language="text",
                    )


def _render_chat_history(chat_container):
    """Render chat history: older pairs collapsed, latest pair expanded."""
    history = st.session_state.chat_history

    if not history:
        with chat_container:
            st.info("Ask a question about your HR data to get started.")
        return

    # Build Q&A pairs: each pair is (user_msg, assistant_msg)
    pairs = []
    i = 0
    while i < len(history):
        if history[i]["role"] == "user":
            user_msg = history[i]
            assistant_msg = history[i + 1] if i + 1 < len(history) and history[i + 1]["role"] == "assistant" else None
            if assistant_msg:
                pairs.append((user_msg, assistant_msg))
                i += 2
            else:
                # User message without response yet -- skip pairing
                i += 1
        else:
            # Orphan assistant message (shouldn't happen) -- skip
            i += 1

    with chat_container:
        if len(pairs) <= 1:
            # Single pair or empty -- render fully expanded
            for msg in history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and msg.get("tool_calls"):
                        tool_calls = msg["tool_calls"]
                        with st.expander(f"Tool calls ({len(tool_calls)})", expanded=False):
                            for tc in tool_calls:
                                st.code(
                                    f"Tool: {tc['tool']}\n"
                                    f"Input: {json.dumps(tc['input'], indent=2)}\n"
                                    f"Result preview: {tc['result'][:500]}...",
                                    language="text",
                                )
        else:
            # Collapse older pairs, expand latest
            for idx, (user_msg, assistant_msg) in enumerate(pairs[:-1]):
                _render_collapsed_pair(user_msg, assistant_msg, idx)

            # Latest pair -- fully expanded
            last_user, last_assistant = pairs[-1]
            with st.chat_message("user"):
                st.markdown(last_user["content"])
            with st.chat_message("assistant"):
                st.markdown(last_assistant.get("content", ""))
                tool_calls = last_assistant.get("tool_calls", [])
                if tool_calls:
                    with st.expander(f"Tool calls ({len(tool_calls)})", expanded=False):
                        for tc in tool_calls:
                            st.code(
                                f"Tool: {tc['tool']}\n"
                                f"Input: {json.dumps(tc['input'], indent=2)}\n"
                                f"Result preview: {tc['result'][:500]}...",
                                language="text",
                            )

        # Also render any trailing user message that has no response yet
        if history and history[-1]["role"] == "user" and (not pairs or pairs[-1][0] is not history[-1]):
            with st.chat_message("user"):
                st.markdown(history[-1]["content"])


def _handle_question(question: str, chat_container):
    """Process a user question: call agent, update history, render response."""
    # Add user message
    st.session_state.chat_history.append({"role": "user", "content": question})

    # Render the user message inside the chat container
    with chat_container:
        with st.chat_message("user"):
            st.markdown(question)

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                tool_log = []

                def on_tool(name, inp, result):
                    tool_log.append({"tool": name, "input": inp, "result": result})
                    try:
                        r = json.loads(result)
                        if "file" in r:
                            st.session_state.latest_viz = r["file"]
                    except (json.JSONDecodeError, TypeError):
                        pass

                try:
                    response = st.session_state.agent.chat(question, on_tool_call=on_tool)
                    st.markdown(response)

                    # Build enhanced assistant message
                    assistant_msg = {
                        "role": "assistant",
                        "content": response,
                        "query": question,
                        "summary": _extract_summary(response),
                        "tags": _extract_tags(response, tool_log),
                        "tool_calls": tool_log,
                    }
                    st.session_state.chat_history.append(assistant_msg)

                    if tool_log:
                        st.session_state.tool_calls.extend(tool_log)
                        with st.expander(f"Tool calls ({len(tool_log)})", expanded=False):
                            for tc in tool_log:
                                st.code(
                                    f"Tool: {tc['tool']}\n"
                                    f"Input: {json.dumps(tc['input'], indent=2)}\n"
                                    f"Result preview: {tc['result'][:500]}...",
                                    language="text",
                                )
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": error_msg}
                    )


def init_agent(api_key: str):
    """Initialize the HR Agent with the given API key."""
    try:
        st.session_state.agent = HRAgent(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
        return False


def load_kpis() -> dict:
    """Load key HR metrics from the graph."""
    try:
        headcount = json.loads(query_graph(
            "MATCH (e:Employee) WHERE e.status = 'Active' RETURN COUNT(e) AS count"
        ))
        turnover = json.loads(query_graph(
            "MATCH (e:Employee) WHERE e.status = 'Terminated' "
            "WITH COUNT(e) AS termed "
            "MATCH (all:Employee) "
            "RETURN termed, COUNT(all) AS total, "
            "round(toFloat(termed) / COUNT(all) * 100, 1) AS turnover_pct"
        ))
        avg_rating = json.loads(query_data_lake(
            "SELECT ROUND(AVG(rating), 2) AS avg_rating FROM performance_reviews"
        ))
        open_reqs = json.loads(query_graph(
            "MATCH (r:Requisition) WHERE r.status = 'Open' RETURN COUNT(r) AS count"
        ))
        diversity = json.loads(query_data_lake(
            "SELECT gender, COUNT(*) AS count FROM employees "
            "WHERE status = 'Active' GROUP BY gender ORDER BY count DESC"
        ))

        return {
            "headcount": headcount.get("rows", [{}])[0].get("count", "?"),
            "turnover_pct": turnover.get("rows", [{}])[0].get("turnover_pct", "?"),
            "avg_rating": avg_rating.get("rows", [{}])[0].get("avg_rating", "?"),
            "open_reqs": open_reqs.get("rows", [{}])[0].get("count", "?"),
            "diversity": {r["gender"]: r["count"] for r in diversity.get("rows", [])},
        }
    except Exception:
        return {
            "headcount": "?", "turnover_pct": "?", "avg_rating": "?",
            "open_reqs": "?", "diversity": {},
        }


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

# --- Inject badge CSS ---
st.markdown(_TAG_BADGE_CSS, unsafe_allow_html=True)

# --- Init agent if API key is set but agent isn't created ---
api_key = st.session_state.get("api_key", "")
if api_key and st.session_state.get("agent") is None:
    init_agent(api_key)


# --- Sidebar example questions ---
with st.sidebar:
    st.subheader("Example Questions")
    example_questions = [
        "Who are the top flight risks in Engineering?",
        "Is there a pay equity gap by gender?",
        "Which recruiting sources produce the best hires?",
        "What happens if Jerry Hayes (EMP-00695) leaves?",
        "Which skills are most common among top performers?",
        "Show me the org chart visualization",
        "What's the average span of control?",
        "Which departments have the most skill overlap?",
    ]
    for q in example_questions:
        if st.button(q, key=f"ex_{hash(q)}", use_container_width=True):
            st.session_state.pending_question = q

    st.divider()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.tool_calls = []
        st.session_state.latest_viz = None
        if st.session_state.get("agent"):
            st.session_state.agent.reset()
        st.rerun()


# --- Main content ---

# KPI bar
kpis = load_kpis()
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Active Headcount", kpis["headcount"])
col2.metric("Turnover Rate", f"{kpis['turnover_pct']}%")
col3.metric("Avg Rating", kpis["avg_rating"])
col4.metric("Open Reqs", kpis["open_reqs"])
diversity = kpis.get("diversity", {})
diversity_str = " / ".join(f"{v}" for v in diversity.values()) if diversity else "?"
col5.metric("Gender Split", diversity_str)

st.divider()

# Layout: Chat (left) + Visualization (right)
chat_col, viz_col = st.columns([3, 2])

with chat_col:
    st.subheader("AI Assistant")

    # Scrollable chat container
    chat_container = st.container(height=550)

    # Render existing chat history (collapsed older pairs, expanded latest)
    _render_chat_history(chat_container)

with viz_col:
    st.subheader("Visualizations")

    # Show latest visualization if available
    if st.session_state.get("latest_viz"):
        viz_path = Path(st.session_state.latest_viz)
        if viz_path.exists():
            st.caption(f"Latest: {viz_path.name}")
            with open(viz_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=500, scrolling=True)

    # List available visualizations
    if EXPORTS_DIR.exists():
        html_files = sorted(EXPORTS_DIR.glob("*.html"))
        if html_files:
            st.caption("Available visualizations:")
            selected_viz = st.selectbox(
                "Select visualization",
                html_files,
                format_func=lambda p: p.stem.replace("_", " ").title(),
                label_visibility="collapsed",
            )
            if selected_viz and selected_viz.exists():
                with open(selected_viz, "r", encoding="utf-8") as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=500, scrolling=True)
        else:
            st.info("No visualizations generated yet. Ask the AI to create one!")
    else:
        st.info("No visualizations available.")

# --- Chat input: pinned to bottom (outside columns) ---
pending = st.session_state.pop("pending_question", None)

user_input = st.chat_input(
    "Ask about your HR data...",
    disabled=not st.session_state.get("agent"),
)

question = pending or user_input

if question and st.session_state.get("agent"):
    _handle_question(question, chat_container)
elif question and not st.session_state.get("agent"):
    st.warning("Please enter your Anthropic API key in the sidebar to use the AI assistant.")

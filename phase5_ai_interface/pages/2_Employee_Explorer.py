"""Employee Explorer page: drill into any employee's ontological data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from phase5_ai_interface.tools.employee_queries import (
    get_employee_list,
    get_employee_summary,
    get_manager_chain,
    get_direct_reports,
    get_skills,
    get_performance_reviews,
    get_goals,
    get_compensation,
    get_temporal_events,
    get_relationship_counts,
)
from phase5_ai_interface.tools.ego_graph import build_ego_graph
from phase4_graph.visualization.style_config import NODE_COLORS


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_employee_option(emp: dict) -> str:
    """Format an employee dict for the selectbox display."""
    dept = emp.get("department") or "Unknown"
    status = emp.get("status") or "?"
    return f"{emp['name']} ({emp['id']}) - {dept} [{status}]"


def _safe_metric(label: str, value, fallback: str = "N/A"):
    """Display a metric, falling back to a default if value is None."""
    st.metric(label, value if value else fallback)


# ── Employee list (cached) ───────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="Loading employees...")
def _load_employees():
    return get_employee_list()


employees = _load_employees()

if not employees:
    st.warning("No employees found. Is Neo4j running?")
    st.stop()


# ── Employee selector ────────────────────────────────────────────────────────

st.header("Employee Explorer")

selected_idx = st.selectbox(
    "Search employee",
    range(len(employees)),
    format_func=lambda i: _format_employee_option(employees[i]),
    placeholder="Type to search...",
)

emp_id = employees[selected_idx]["id"]


# ── Summary cards ────────────────────────────────────────────────────────────

summary = get_employee_summary(emp_id)

if not summary:
    st.error(f"Could not load data for {emp_id}")
    st.stop()

st.subheader(f"{summary.get('name', emp_id)}")

row1_cols = st.columns(4)
row1_cols[0].metric("Position", summary.get("position") or "N/A")
row1_cols[1].metric("Level", summary.get("job_level") or "N/A")
row1_cols[2].metric("Department", summary.get("department") or "N/A")
row1_cols[3].metric("Status", summary.get("status") or "N/A")

row2_cols = st.columns(4)
row2_cols[0].metric("Division", summary.get("division") or "N/A")
row2_cols[1].metric("Location", summary.get("location") or "N/A")
row2_cols[2].metric("Hire Date", summary.get("hire_date") or "N/A")
row2_cols[3].metric("Manager", summary.get("manager_name") or "None (CEO)")

st.divider()


# ── Ego-graph + Relationship summary ────────────────────────────────────────

graph_col, rel_col = st.columns([3, 1])

with graph_col:
    st.subheader("Relationship Graph")
    hop_count = st.radio("Hops", [1, 2], horizontal=True, index=0)

    with st.spinner("Building ego-graph..."):
        graph_path = build_ego_graph(emp_id, hops=hop_count)

    if graph_path and Path(graph_path).exists():
        with open(graph_path, "r", encoding="utf-8") as f:
            html = f.read()
        st.components.v1.html(html, height=620, scrolling=False)
    else:
        st.info("No relationships found for this employee.")

    # Color legend
    with st.expander("Node Color Legend", expanded=False):
        legend_cols = st.columns(4)
        for i, (label, color) in enumerate(NODE_COLORS.items()):
            col = legend_cols[i % 4]
            col.markdown(
                f'<span style="color:{color}">&#9679;</span> {label}',
                unsafe_allow_html=True,
            )

with rel_col:
    st.subheader("Relationships")
    rel_counts = get_relationship_counts(emp_id)
    if rel_counts:
        total = sum(r["count"] for r in rel_counts)
        st.metric("Total Relationships", total)
        st.divider()
        for r in rel_counts:
            st.markdown(f"**{r['relationship']}**: {r['count']}")
    else:
        st.caption("No relationships found.")

st.divider()


# ── Detail tabs ──────────────────────────────────────────────────────────────

tab_org, tab_skills, tab_perf, tab_comp, tab_hist = st.tabs(
    ["Org Structure", "Skills", "Performance", "Compensation", "History"]
)


# --- Org Structure ---
with tab_org:
    org_left, org_right = st.columns(2)

    with org_left:
        st.markdown("#### Manager Chain")
        chain = get_manager_chain(emp_id)
        if chain:
            for i, mgr in enumerate(chain):
                indent = "\u2003" * i
                arrow = "\u2191 " if i > 0 else ""
                level = mgr.get("job_level") or ""
                st.markdown(f"{indent}{arrow}**{mgr['name']}** ({level})")
        else:
            st.caption("No manager chain (top of hierarchy).")

    with org_right:
        st.markdown("#### Direct Reports")
        reports = get_direct_reports(emp_id)
        if reports:
            st.caption(f"{len(reports)} direct report(s)")
            for r in reports:
                status_badge = "" if r.get("status") == "Active" else f" [{r.get('status')}]"
                position = r.get("position") or ""
                st.markdown(f"- **{r['name']}** -- {position} ({r.get('job_level', '')}){status_badge}")
        else:
            st.caption("No direct reports (individual contributor).")


# --- Skills ---
with tab_skills:
    skill_data = get_skills(emp_id)
    if skill_data:
        # Group by category
        categories = {}
        for s in skill_data:
            cat = s.get("category") or "Uncategorized"
            categories.setdefault(cat, []).append(s)

        for cat, skills_list in sorted(categories.items()):
            st.markdown(f"#### {cat}")
            for s in skills_list:
                prof = s.get("proficiency") or "?"
                assessed = s.get("assessed_date") or ""
                assessed_str = f" (assessed {assessed})" if assessed else ""
                st.markdown(f"- **{s['name']}** -- proficiency: {prof}{assessed_str}")
    else:
        st.caption("No skills recorded for this employee.")


# --- Performance ---
with tab_perf:
    perf_left, perf_right = st.columns(2)

    with perf_left:
        st.markdown("#### Reviews")
        reviews = get_performance_reviews(emp_id)
        if reviews:
            for rev in reviews:
                cycle = rev.get("cycle_name") or "N/A"
                reviewer = rev.get("reviewer_name") or "N/A"
                rating = rev.get("rating") or "?"
                date = rev.get("review_date") or ""
                st.markdown(f"**{cycle}** -- Rating: **{rating}** | Reviewer: {reviewer} | {date}")
                if rev.get("comments"):
                    st.caption(rev["comments"][:200])
        else:
            st.caption("No performance reviews found.")

    with perf_right:
        st.markdown("#### Goals")
        goals = get_goals(emp_id)
        if goals:
            for g in goals:
                status = g.get("status") or "?"
                achievement = g.get("achievement_pct")
                ach_str = f" ({achievement}%)" if achievement is not None else ""
                cycle = g.get("cycle_name") or ""
                cycle_str = f" [{cycle}]" if cycle else ""
                desc = g.get("description") or "No description"
                st.markdown(f"- **{status}**{ach_str}{cycle_str}: {desc[:100]}")
        else:
            st.caption("No goals found.")


# --- Compensation ---
with tab_comp:
    comp = get_compensation(emp_id)

    # Salary band context
    band = comp.get("salary_band", {})
    if band:
        st.markdown("#### Salary Band")
        band_cols = st.columns(4)
        band_cols[0].metric("Job Family", band.get("job_family") or "N/A")
        band_cols[1].metric("Min", f"${band.get('min_salary', 0):,.0f}" if band.get("min_salary") else "N/A")
        band_cols[2].metric("Midpoint", f"${band.get('midpoint', 0):,.0f}" if band.get("midpoint") else "N/A")
        band_cols[3].metric("Max", f"${band.get('max_salary', 0):,.0f}" if band.get("max_salary") else "N/A")
        st.divider()

    comp_left, comp_mid, comp_right = st.columns(3)

    with comp_left:
        st.markdown("#### Salary History")
        salaries = comp.get("salaries", [])
        if salaries:
            for s in salaries:
                amount = s.get("amount")
                amt_str = f"${amount:,.0f}" if amount else "?"
                date = s.get("effective_date") or ""
                freq = s.get("pay_frequency") or ""
                st.markdown(f"- **{amt_str}** {freq} (effective {date})")
        else:
            st.caption("No salary records.")

    with comp_mid:
        st.markdown("#### Bonuses")
        bonuses = comp.get("bonuses", [])
        if bonuses:
            for b in bonuses:
                amount = b.get("amount")
                amt_str = f"${amount:,.0f}" if amount else "?"
                btype = b.get("type") or ""
                date = b.get("payment_date") or ""
                st.markdown(f"- **{amt_str}** {btype} ({date})")
        else:
            st.caption("No bonus records.")

    with comp_right:
        st.markdown("#### Equity Grants")
        equity = comp.get("equity", [])
        if equity:
            for eq in equity:
                shares = eq.get("shares") or "?"
                date = eq.get("grant_date") or ""
                strike = eq.get("strike_price")
                strike_str = f" @ ${strike}" if strike else ""
                vesting = eq.get("vesting_schedule") or ""
                st.markdown(f"- **{shares} shares**{strike_str} ({date}) {vesting}")
        else:
            st.caption("No equity grants.")


# --- History ---
with tab_hist:
    events = get_temporal_events(emp_id)
    if events:
        st.markdown("#### Lifecycle Timeline")
        for ev in events:
            event_type = ev.get("event_type") or "Event"
            date = ev.get("event_date") or ""
            desc = ev.get("description") or ""
            st.markdown(f"- **{date}** -- {event_type}: {desc}")
    else:
        st.caption("No lifecycle events recorded.")

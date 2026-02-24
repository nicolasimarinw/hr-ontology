"""End-to-end validation: 8 CHRO queries against graph + data lake.

Tests each query via both Cypher (Neo4j) and SQL (DuckDB) where applicable,
measures response times, and validates results.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from phase5_ai_interface.tools.cypher_tools import query_graph
from phase5_ai_interface.tools.duckdb_tools import query_data_lake
from phase5_ai_interface.tools.visualization_tools import run_graph_algorithm

console = Console()
results = []


def timed(func, *args, **kwargs):
    """Execute a function and return (result, elapsed_seconds)."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def validate(name, result_json, elapsed, approach, min_rows=0):
    """Validate a query result and record it."""
    data = json.loads(result_json)
    has_error = "error" in data
    row_count = len(data.get("rows", [])) if "rows" in data else None

    passed = not has_error and (row_count is None or row_count >= min_rows)
    status = "PASS" if passed else "FAIL"

    results.append({
        "query": name,
        "approach": approach,
        "elapsed": elapsed,
        "rows": row_count,
        "passed": passed,
        "error": data.get("error"),
    })

    icon = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
    console.print(f"  {icon} [{approach}] {elapsed:.2f}s | {row_count or '?'} rows")
    if has_error:
        console.print(f"    Error: {data['error'][:100]}")

    return data


# =============================================================================
# Query 1: Flight risks in Engineering + cascade impact
# =============================================================================
console.print(Panel("[bold]Q1: Who are the top flight risks in Engineering and what would happen if they left?[/bold]"))

# Graph approach: traverse relationships to compute impact score
r, t = timed(query_graph, """
    MATCH (e:Employee)-[:BELONGS_TO]->(d:Department)-[:PART_OF]->(div:Division)
    WHERE e.status = 'Active' AND div.name CONTAINS 'Engineering'
    OPTIONAL MATCH (report:Employee)-[:REPORTS_TO]->(e)
    WITH e, d, div, COUNT(report) AS direct_reports
    OPTIONAL MATCH (e)-[:HAS_SKILL]->(s:Skill)
    WITH e, d, div, direct_reports, COUNT(DISTINCT s) AS skill_count
    WITH e, d, div, direct_reports, skill_count,
         (direct_reports * 10 + skill_count * 2) AS impact_score
    WHERE impact_score > 0
    ORDER BY impact_score DESC
    LIMIT 10
    RETURN e.employee_id AS id, e.first_name + ' ' + e.last_name AS name,
           e.job_level AS level, d.name AS department, div.name AS division,
           direct_reports, skill_count, impact_score
""")
data = validate("Q1: Flight risks (Engineering)", r, t, "graph", min_rows=1)

# Cascade for the top risk
if data.get("rows"):
    top_emp = data["rows"][0]["id"]
    r2, t2 = timed(run_graph_algorithm, "cascade", employee_id=top_emp)
    cascade = json.loads(r2)
    console.print(f"  Cascade for {data['rows'][0]['name']}:")
    console.print(f"    Direct reports orphaned: {len(cascade.get('direct_reports', []))}")
    console.print(f"    Skills lost: {len(cascade.get('skills_lost', []))}")
    console.print(f"    Goals orphaned: {cascade.get('active_goals_orphaned', 0)}")

# SQL cannot easily do multi-hop traversal
console.print("  [dim]SQL: Not feasible (requires multi-hop relationship traversal)[/dim]")
console.print()


# =============================================================================
# Query 2: Pay equity gap by gender for senior engineers
# =============================================================================
console.print(Panel("[bold]Q2: Is there a pay equity gap by gender for senior engineers?[/bold]"))

# SQL approach: aggregate with cross-tabulation
r, t = timed(query_data_lake, """
    SELECT e.gender, e.job_level,
           COUNT(*) AS headcount,
           ROUND(AVG(bs.amount), 0) AS avg_salary,
           ROUND(MEDIAN(bs.amount), 0) AS median_salary,
           ROUND(STDDEV(bs.amount), 0) AS std_salary
    FROM employees e
    JOIN base_salary bs ON e.employee_id = bs.employee_id
    WHERE e.status = 'Active'
      AND e.job_family = 'JF-ENG'
      AND e.job_level IN ('L3', 'L4', 'M1', 'M2')
      AND bs.effective_date = (
          SELECT MAX(bs2.effective_date)
          FROM base_salary bs2
          WHERE bs2.employee_id = e.employee_id
      )
    GROUP BY e.gender, e.job_level
    ORDER BY e.job_level, e.gender
""")
data = validate("Q2: Pay equity (senior eng)", r, t, "sql", min_rows=1)
if data.get("rows"):
    for row in data["rows"]:
        console.print(f"    {row['gender']:12s} {row['job_level']:4s} n={row['headcount']:3d}  avg=${row['avg_salary']:>10,.0f}  med=${row['median_salary']:>10,.0f}")

# Graph approach: possible but slower for aggregation
r, t = timed(query_graph, """
    MATCH (e:Employee)-[:EARNS_BASE]->(bs:BaseSalary)
    WHERE e.status = 'Active' AND e.job_family = 'Software Engineering'
      AND e.job_level IN ['L3', 'L4', 'M1', 'M2']
    WITH e, bs ORDER BY bs.effective_date DESC
    WITH e, COLLECT(bs)[0] AS latest
    RETURN e.gender AS gender, e.job_level AS level,
           COUNT(e) AS headcount, round(avg(latest.amount)) AS avg_salary
    ORDER BY level, gender
""")
validate("Q2: Pay equity (graph alt)", r, t, "graph")
console.print()


# =============================================================================
# Query 3: Recruiting sources -> performance correlation
# =============================================================================
console.print(Panel("[bold]Q3: Which recruiting sources produce the highest-performing hires?[/bold]"))

# SQL approach
r, t = timed(query_data_lake, """
    SELECT c.source,
           COUNT(DISTINCT e.employee_id) AS hires,
           ROUND(AVG(pr.rating), 2) AS avg_performance_rating,
           ROUND(AVG(CASE WHEN e.status = 'Terminated' THEN 1.0 ELSE 0.0 END) * 100, 1) AS turnover_pct
    FROM candidates c
    JOIN applications a ON c.candidate_id = a.candidate_id
    JOIN offers o ON a.application_id = o.application_id
    JOIN employees e ON e.email = c.email
    LEFT JOIN performance_reviews pr ON pr.employee_id = e.employee_id
    WHERE o.status = 'Accepted'
    GROUP BY c.source
    HAVING COUNT(DISTINCT e.employee_id) >= 3
    ORDER BY avg_performance_rating DESC
""")
data = validate("Q3: Source -> performance", r, t, "sql", min_rows=1)
if data.get("rows"):
    for row in data["rows"]:
        console.print(f"    {row['source']:15s} hires={row['hires']:3d}  rating={row['avg_performance_rating']:.2f}  turnover={row['turnover_pct']}%")

# Graph approach: traverse source -> candidate -> hire -> review
r, t = timed(query_graph, """
    MATCH (sc:SourceChannel)<-[:SOURCED_FROM]-(c:Candidate)
    MATCH (c)-[:HAS_APPLICATION]->(app:Application)-[:HAS_OFFER]->(o:Offer)
    WHERE o.status = 'Accepted'
    WITH sc, COUNT(DISTINCT c) AS candidates_hired
    RETURN sc.channel_name AS source, candidates_hired
    ORDER BY candidates_hired DESC
""")
validate("Q3: Source -> hire count (graph)", r, t, "graph")
console.print()


# =============================================================================
# Query 4: Succession pipeline for director+ positions
# =============================================================================
console.print(Panel("[bold]Q4: Show me the succession pipeline for all director+ positions[/bold]"))

# Graph approach: find directors and their potential successors
r, t = timed(query_graph, """
    MATCH (mgr:Employee)<-[:REPORTS_TO]-(report:Employee)
    WHERE mgr.status = 'Active' AND mgr.job_level IN ['D1', 'D2', 'VP', 'CX']
      AND report.status = 'Active'
    WITH mgr, report
    OPTIONAL MATCH (report)-[:HAS_SKILL]->(s:Skill)
    WITH mgr, report, COUNT(s) AS skill_count
    OPTIONAL MATCH (report)-[:REVIEWED_IN]->(r:PerformanceReview)
    WITH mgr, report, skill_count, AVG(r.rating) AS avg_rating
    RETURN mgr.employee_id AS leader_id,
           mgr.first_name + ' ' + mgr.last_name AS leader_name,
           mgr.job_level AS leader_level,
           report.employee_id AS successor_id,
           report.first_name + ' ' + report.last_name AS successor_name,
           report.job_level AS successor_level,
           skill_count, round(avg_rating * 100) / 100 AS avg_rating
    ORDER BY leader_level DESC, avg_rating DESC
""")
data = validate("Q4: Succession pipeline", r, t, "graph", min_rows=1)
if data.get("rows"):
    console.print(f"    Found {len(data['rows'])} leader-successor pairs")
    for row in data["rows"][:5]:
        console.print(f"    {row['leader_name']} ({row['leader_level']}) <- {row['successor_name']} ({row['successor_level']}) rating={row.get('avg_rating', '?')}")
console.print("  [dim]SQL: Would require self-joins + subqueries (graph is more natural)[/dim]")
console.print()


# =============================================================================
# Query 5: Manager rating variance across demographics (bias detection)
# =============================================================================
console.print(Panel("[bold]Q5: Which managers have the most rating variance across demographics?[/bold]"))

# SQL approach: cross-tabulate manager ratings by gender
r, t = timed(query_data_lake, """
    SELECT pr.reviewer_id AS manager_id,
           e_mgr.first_name || ' ' || e_mgr.last_name AS manager_name,
           e_mgr.department_id AS dept,
           COUNT(*) AS reviews_given,
           ROUND(AVG(CASE WHEN e.gender = 'Male' THEN pr.rating END), 2) AS avg_male,
           ROUND(AVG(CASE WHEN e.gender = 'Female' THEN pr.rating END), 2) AS avg_female,
           ROUND(ABS(
               AVG(CASE WHEN e.gender = 'Male' THEN pr.rating END) -
               AVG(CASE WHEN e.gender = 'Female' THEN pr.rating END)
           ), 2) AS gender_gap
    FROM performance_reviews pr
    JOIN employees e ON pr.employee_id = e.employee_id
    JOIN employees e_mgr ON pr.reviewer_id = e_mgr.employee_id
    WHERE pr.reviewer_id IS NOT NULL
    GROUP BY pr.reviewer_id, e_mgr.first_name, e_mgr.last_name, e_mgr.department_id
    HAVING COUNT(*) >= 5
       AND COUNT(CASE WHEN e.gender = 'Male' THEN 1 END) >= 2
       AND COUNT(CASE WHEN e.gender = 'Female' THEN 1 END) >= 2
    ORDER BY gender_gap DESC
    LIMIT 10
""")
data = validate("Q5: Rating bias by manager", r, t, "sql", min_rows=1)
if data.get("rows"):
    for row in data["rows"][:5]:
        console.print(f"    {row['manager_name']:20s} reviews={row['reviews_given']:2d}  M={row['avg_male']:.2f}  F={row['avg_female']:.2f}  gap={row['gender_gap']:.2f}")
console.print()


# =============================================================================
# Query 6: Promotion velocity by gender
# =============================================================================
console.print(Panel("[bold]Q6: What's the promotion velocity difference by gender in the last 2 years?[/bold]"))

# SQL approach
r, t = timed(query_data_lake, """
    SELECT e.gender,
           COUNT(*) AS promotions,
           ROUND(AVG(DATEDIFF('month', e.hire_date, eh.effective_date)), 1) AS avg_months_to_promote,
           ROUND(MEDIAN(DATEDIFF('month', e.hire_date, eh.effective_date)), 1) AS median_months
    FROM employment_history eh
    JOIN employees e ON eh.employee_id = e.employee_id
    WHERE eh.event_type = 'Promotion'
      AND eh.effective_date >= '2024-01-01'
    GROUP BY e.gender
    ORDER BY e.gender
""")
data = validate("Q6: Promotion velocity", r, t, "sql", min_rows=1)
if data.get("rows"):
    for row in data["rows"]:
        console.print(f"    {row['gender']:12s} promotions={row['promotions']:3d}  avg_months={row['avg_months_to_promote']:5.1f}  median={row['median_months']:5.1f}")

# Graph approach
r, t = timed(query_graph, """
    MATCH (e:Employee)-[:EXPERIENCED_EVENT]->(evt:TemporalEvent)
    WHERE evt.event_type = 'promotion' AND evt.effective_date >= '2024-01-01'
    RETURN e.gender AS gender, COUNT(*) AS promotions
    ORDER BY gender
""")
validate("Q6: Promotion count (graph)", r, t, "graph")
console.print()


# =============================================================================
# Query 7: VP of Engineering cascade impact
# =============================================================================
console.print(Panel("[bold]Q7: If our VP of Engineering leaves, map the full organizational impact[/bold]"))

# Find the VP first
r, t = timed(query_graph, """
    MATCH (e:Employee)
    WHERE e.status = 'Active' AND e.job_level = 'VP'
    OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Department)-[:PART_OF]->(div:Division)
    RETURN e.employee_id AS id, e.first_name + ' ' + e.last_name AS name,
           e.job_level AS level, div.name AS division
""")
vp_data = validate("Q7: Find VPs", r, t, "graph", min_rows=1)

if vp_data.get("rows"):
    # Run cascade for the first VP found
    vp = vp_data["rows"][0]
    console.print(f"  Running cascade for {vp['name']} ({vp.get('division', '?')})...")
    r2, t2 = timed(run_graph_algorithm, "cascade", employee_id=vp["id"])
    cascade = json.loads(r2)
    results.append({
        "query": "Q7: VP cascade impact",
        "approach": "algorithm",
        "elapsed": t2,
        "rows": None,
        "passed": "error" not in cascade,
        "error": cascade.get("error"),
    })
    if "error" not in cascade:
        emp = cascade.get("employee", {})
        console.print(f"    [green]PASS[/green] [algorithm] {t2:.2f}s")
        console.print(f"    Employee: {emp.get('name')} ({emp.get('level')})")
        console.print(f"    Direct reports orphaned: {len(cascade.get('direct_reports', []))}")
        console.print(f"    Indirect reports affected: {cascade.get('indirect_report_count', 0)}")
        console.print(f"    Employees losing reviewer: {cascade.get('employees_reviewed', 0)}")
        console.print(f"    Skills lost: {cascade.get('skills_lost', [])}")
        console.print(f"    Active goals orphaned: {cascade.get('active_goals_orphaned', 0)}")
    else:
        console.print(f"    [red]FAIL[/red]: {cascade.get('error')}")

console.print("  [dim]SQL: Cannot traverse arbitrary-depth relationships[/dim]")
console.print()


# =============================================================================
# Query 8: Skills of top vs bottom performers
# =============================================================================
console.print(Panel("[bold]Q8: Which skills are most common among top performers vs bottom performers?[/bold]"))

# Graph approach: traverse employee -> review -> skill
r, t = timed(query_graph, """
    MATCH (e:Employee)-[:REVIEWED_IN]->(r:PerformanceReview)
    WHERE e.status = 'Active'
    WITH e, AVG(r.rating) AS avg_rating
    WITH e, avg_rating,
         CASE WHEN avg_rating >= 4.0 THEN 'top'
              WHEN avg_rating <= 2.5 THEN 'bottom'
              ELSE 'middle' END AS tier
    WHERE tier IN ['top', 'bottom']
    MATCH (e)-[:HAS_SKILL]->(s:Skill)
    WITH tier, s.name AS skill, s.category AS category, COUNT(DISTINCT e) AS employee_count
    ORDER BY tier, employee_count DESC
    RETURN tier, skill, category, employee_count
""")
data = validate("Q8: Skills by performer tier", r, t, "graph", min_rows=1)
if data.get("rows"):
    top_skills = [r for r in data["rows"] if r["tier"] == "top"][:5]
    bottom_skills = [r for r in data["rows"] if r["tier"] == "bottom"][:5]
    console.print("    Top performer skills:")
    for s in top_skills:
        console.print(f"      {s['skill']:25s} ({s['category']}) n={s['employee_count']}")
    console.print("    Bottom performer skills:")
    for s in bottom_skills:
        console.print(f"      {s['skill']:25s} ({s['category']}) n={s['employee_count']}")

console.print("  [dim]SQL: Would need multiple joins; graph is far more natural[/dim]")
console.print()


# =============================================================================
# Summary
# =============================================================================
console.print(Panel("[bold blue]Validation Summary[/bold blue]"))

table = Table()
table.add_column("Query", style="cyan", width=35)
table.add_column("Approach", width=10)
table.add_column("Time (s)", justify="right", width=10)
table.add_column("Rows", justify="right", width=6)
table.add_column("Status", justify="center", width=8)

for r in results:
    status = "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]"
    table.add_row(
        r["query"], r["approach"],
        f"{r['elapsed']:.2f}", str(r["rows"] or "-"),
        status,
    )

console.print(table)

total = len(results)
passed = sum(1 for r in results if r["passed"])
failed = total - passed
avg_time = sum(r["elapsed"] for r in results) / total if total > 0 else 0

console.print(f"\n[bold]Results: {passed}/{total} passed, {failed} failed[/bold]")
console.print(f"[bold]Average response time: {avg_time:.2f}s[/bold]")
console.print(f"[bold]All under 30s: {'YES' if all(r['elapsed'] < 30 for r in results) else 'NO'}[/bold]")

# Write results to JSON for the report
output = {
    "results": results,
    "summary": {
        "total": total,
        "passed": passed,
        "failed": failed,
        "avg_time_seconds": round(avg_time, 2),
        "all_under_30s": all(r["elapsed"] < 30 for r in results),
    }
}
output_path = Path(__file__).parent.parent / "data" / "exports" / "validation_results.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w") as f:
    json.dump(output, f, indent=2, default=str)
console.print(f"\nResults saved to {output_path}")

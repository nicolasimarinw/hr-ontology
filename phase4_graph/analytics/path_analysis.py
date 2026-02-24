"""Path analysis: cascade impact, shortest paths, organizational distance."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from phase4_graph.loader.neo4j_connection import Neo4jConnection

console = Console()


def cascade_impact(conn: Neo4jConnection, employee_id: str) -> dict:
    """Analyze the full organizational impact if an employee departs.

    Traverses: direct reports, reviews given, interviews conducted,
    salary/compensation relationships, and goals.
    """
    # Get employee info
    emp_info = conn.run("""
        MATCH (e:Employee {employee_id: $eid})
        RETURN e.first_name + ' ' + e.last_name AS name,
               e.job_level AS level,
               e.department_id AS dept
    """, eid=employee_id)

    if not emp_info:
        return {"error": f"Employee {employee_id} not found"}

    # Direct reports left without manager
    direct_reports = conn.run("""
        MATCH (report:Employee)-[:REPORTS_TO]->(e:Employee {employee_id: $eid})
        RETURN report.employee_id AS id,
               report.first_name + ' ' + report.last_name AS name,
               report.job_level AS level
    """, eid=employee_id)

    # Indirect reports (2 levels deep)
    indirect_reports = conn.run("""
        MATCH (indirect:Employee)-[:REPORTS_TO*2]->(e:Employee {employee_id: $eid})
        RETURN COUNT(indirect) AS count
    """, eid=employee_id)

    # Performance reviews this person gives (as reviewer)
    reviews_given = conn.run("""
        MATCH (r:PerformanceReview)-[:REVIEWED_BY]->(e:Employee {employee_id: $eid})
        MATCH (emp:Employee)-[:REVIEWED_IN]->(r)
        RETURN COUNT(DISTINCT emp) AS employees_reviewed
    """, eid=employee_id)

    # Interviews conducted
    interviews = conn.run("""
        MATCH (i:Interview)-[:INTERVIEWED_BY]->(e:Employee {employee_id: $eid})
        RETURN COUNT(i) AS interview_count
    """, eid=employee_id)

    # Skills this person has (knowledge loss)
    skills = conn.run("""
        MATCH (e:Employee {employee_id: $eid})-[:HAS_SKILL]->(s:Skill)
        RETURN s.name AS skill_name
    """, eid=employee_id)

    # Goals that would be orphaned
    goals = conn.run("""
        MATCH (e:Employee {employee_id: $eid})-[:SET_GOAL]->(g:Goal)
        WHERE g.status <> 'Completed'
        RETURN COUNT(g) AS active_goals
    """, eid=employee_id)

    return {
        "employee": emp_info[0],
        "direct_reports": direct_reports,
        "indirect_report_count": indirect_reports[0]["count"] if indirect_reports else 0,
        "employees_reviewed": reviews_given[0]["employees_reviewed"] if reviews_given else 0,
        "interviews_conducted": interviews[0]["interview_count"] if interviews else 0,
        "skills_lost": [s["skill_name"] for s in skills],
        "active_goals_orphaned": goals[0]["active_goals"] if goals else 0,
    }


def org_distance(conn: Neo4jConnection, emp1_id: str, emp2_id: str) -> dict:
    """Find the shortest organizational path between two employees."""
    result = conn.run("""
        MATCH path = shortestPath(
            (e1:Employee {employee_id: $eid1})-[:REPORTS_TO*]-(e2:Employee {employee_id: $eid2})
        )
        RETURN [n IN nodes(path) |
            n.first_name + ' ' + n.last_name + ' (' + n.job_level + ')'] AS path_names,
               length(path) AS distance
    """, eid1=emp1_id, eid2=emp2_id)

    if result:
        return {"path": result[0]["path_names"], "distance": result[0]["distance"]}
    return {"path": [], "distance": -1}


def flight_risk_cascade(conn: Neo4jConnection, top_n: int = 10) -> list[dict]:
    """Identify high-impact flight risks by combining risk score with cascade impact.

    Employees with both high flight risk AND high organizational impact.
    """
    results = conn.run("""
        MATCH (e:Employee)
        WHERE e.status = 'Active'
        OPTIONAL MATCH (report:Employee)-[:REPORTS_TO]->(e)
        WITH e, COUNT(report) AS direct_reports
        OPTIONAL MATCH (r:PerformanceReview)-[:REVIEWED_BY]->(e)
        WITH e, direct_reports, COUNT(r) AS reviews_given
        OPTIONAL MATCH (e)-[:HAS_SKILL]->(s:Skill)
        WITH e, direct_reports, reviews_given, COUNT(s) AS skill_count
        WITH e, direct_reports, reviews_given, skill_count,
             (direct_reports * 10 + reviews_given * 3 + skill_count * 2) AS impact_score
        WHERE impact_score > 0
        RETURN e.employee_id AS employee_id,
               e.first_name + ' ' + e.last_name AS name,
               e.job_level AS level,
               e.department_id AS dept,
               direct_reports,
               reviews_given,
               skill_count,
               impact_score
        ORDER BY impact_score DESC
        LIMIT $top_n
    """, top_n=top_n)
    return results


def print_cascade_report(conn: Neo4jConnection, employee_id: str) -> None:
    """Print a detailed cascade impact report for an employee."""
    impact = cascade_impact(conn, employee_id)

    if "error" in impact:
        console.print(f"[red]{impact['error']}[/red]")
        return

    emp = impact["employee"]
    console.print(f"\n[bold blue]Cascade Impact Report: {emp['name']}[/bold blue]")
    console.print(f"Level: {emp['level']} | Dept: {emp['dept']}\n")

    tree = Tree(f"[bold]{emp['name']}[/bold] departs")

    # Direct reports
    dr_branch = tree.add(f"[red]Direct reports orphaned: {len(impact['direct_reports'])}[/red]")
    for r in impact["direct_reports"]:
        dr_branch.add(f"{r['name']} ({r['level']})")

    # Indirect
    tree.add(f"[yellow]Indirect reports affected: {impact['indirect_report_count']}[/yellow]")

    # Reviews
    tree.add(f"Employees losing reviewer: {impact['employees_reviewed']}")

    # Interviews
    tree.add(f"Interview pipeline disrupted: {impact['interviews_conducted']} interviews")

    # Skills
    if impact["skills_lost"]:
        skill_branch = tree.add(f"[cyan]Knowledge loss: {len(impact['skills_lost'])} skills[/cyan]")
        for s in impact["skills_lost"]:
            skill_branch.add(s)

    # Goals
    tree.add(f"Active goals orphaned: {impact['active_goals_orphaned']}")

    console.print(tree)


def print_flight_risk_report(conn: Neo4jConnection) -> None:
    """Print top flight risks by organizational impact."""
    console.print("\n[bold blue]High-Impact Flight Risks[/bold blue]\n")

    risks = flight_risk_cascade(conn, 15)
    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Level")
    table.add_column("Dept")
    table.add_column("Direct Reports", justify="right")
    table.add_column("Reviews Given", justify="right")
    table.add_column("Skills", justify="right")
    table.add_column("Impact Score", justify="right", style="bold green")

    for r in risks:
        table.add_row(
            r["name"], r["level"], r["dept"],
            str(r["direct_reports"]), str(r["reviews_given"]),
            str(r["skill_count"]), str(r["impact_score"]),
        )

    console.print(table)


if __name__ == "__main__":
    conn = Neo4jConnection()
    if conn.verify():
        print_flight_risk_report(conn)
    conn.close()

"""Community detection: discover informal organizational clusters."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from collections import Counter

from rich.console import Console
from rich.table import Table

from phase4_graph.loader.neo4j_connection import Neo4jConnection

console = Console()


def department_clusters(conn: Neo4jConnection) -> list[dict]:
    """Analyze how departments cluster by shared relationships.

    Find departments connected through cross-department interview,
    review, and reporting relationships.
    """
    results = conn.run("""
        MATCH (e1:Employee)-[:REPORTS_TO]->(e2:Employee)
        WHERE e1.department_id <> e2.department_id
        WITH e1.department_id AS dept1, e2.department_id AS dept2, COUNT(*) AS cross_reports
        RETURN dept1, dept2, cross_reports
        ORDER BY cross_reports DESC
        LIMIT 20
    """)
    return results


def skill_communities(conn: Neo4jConnection) -> list[dict]:
    """Find communities of employees connected through shared skills.

    Employees who share 2+ skills are considered in the same skill community.
    """
    results = conn.run("""
        MATCH (e1:Employee)-[:HAS_SKILL]->(s:Skill)<-[:HAS_SKILL]-(e2:Employee)
        WHERE e1.employee_id < e2.employee_id
        WITH e1, e2, COUNT(DISTINCT s) AS shared_skills
        WHERE shared_skills >= 2
        RETURN e1.employee_id AS emp1_id,
               e1.first_name + ' ' + e1.last_name AS emp1_name,
               e1.department_id AS emp1_dept,
               e2.employee_id AS emp2_id,
               e2.first_name + ' ' + e2.last_name AS emp2_name,
               e2.department_id AS emp2_dept,
               shared_skills
        ORDER BY shared_skills DESC
        LIMIT 30
    """)
    return results


def interview_network(conn: Neo4jConnection) -> list[dict]:
    """Find cross-department collaboration through interview relationships.

    Interviewers from different departments create informal connections.
    """
    results = conn.run("""
        MATCH (i:Interview)-[:INTERVIEWED_BY]->(emp:Employee)
        MATCH (app:Application)-[:HAS_INTERVIEW]->(i)
        MATCH (app)-[:APPLICATION_FOR]->(req:Requisition)
        WHERE emp.department_id <> req.department_id
        WITH emp.department_id AS interviewer_dept,
             req.department_id AS hiring_dept,
             COUNT(*) AS cross_interviews
        RETURN interviewer_dept, hiring_dept, cross_interviews
        ORDER BY cross_interviews DESC
        LIMIT 20
    """)
    return results


def department_diversity_profile(conn: Neo4jConnection) -> list[dict]:
    """Profile each department by gender and ethnicity distribution."""
    results = conn.run("""
        MATCH (e:Employee)
        WHERE e.status = 'Active'
        WITH e.department_id AS dept,
             e.gender AS gender,
             COUNT(*) AS count
        RETURN dept, gender, count
        ORDER BY dept, count DESC
    """)
    return results


def print_community_report(conn: Neo4jConnection) -> None:
    """Print community detection analysis."""
    console.print("\n[bold blue]Community Detection[/bold blue]\n")

    # Cross-department reporting
    console.print("[bold]Cross-Department Reporting Relationships:[/bold]")
    clusters = department_clusters(conn)
    if clusters:
        table = Table()
        table.add_column("Dept 1", style="cyan")
        table.add_column("Dept 2", style="cyan")
        table.add_column("Cross Reports", justify="right", style="green")
        for r in clusters[:10]:
            table.add_row(r["dept1"], r["dept2"], str(r["cross_reports"]))
        console.print(table)
    else:
        console.print("  No cross-department reporting found.")

    # Skill communities
    console.print("\n[bold]Skill-Based Communities (employees sharing 2+ skills):[/bold]")
    skills = skill_communities(conn)
    if skills:
        table = Table()
        table.add_column("Employee 1", style="cyan")
        table.add_column("Dept", style="dim")
        table.add_column("Employee 2", style="cyan")
        table.add_column("Dept", style="dim")
        table.add_column("Shared Skills", justify="right", style="green")
        for r in skills[:10]:
            table.add_row(r["emp1_name"], r["emp1_dept"],
                         r["emp2_name"], r["emp2_dept"],
                         str(r["shared_skills"]))
        console.print(table)
    else:
        console.print("  No skill communities found (need HAS_SKILL edges).")

    # Interview network
    console.print("\n[bold]Cross-Department Interview Network:[/bold]")
    interviews = interview_network(conn)
    if interviews:
        table = Table()
        table.add_column("Interviewer Dept", style="cyan")
        table.add_column("Hiring Dept", style="cyan")
        table.add_column("Cross Interviews", justify="right", style="green")
        for r in interviews[:10]:
            table.add_row(r["interviewer_dept"], r["hiring_dept"], str(r["cross_interviews"]))
        console.print(table)
    else:
        console.print("  No cross-department interviews found.")


if __name__ == "__main__":
    conn = Neo4jConnection()
    if conn.verify():
        print_community_report(conn)
    conn.close()

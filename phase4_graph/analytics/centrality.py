"""Centrality analysis: PageRank, betweenness, degree centrality."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.table import Table

from phase4_graph.loader.neo4j_connection import Neo4jConnection

console = Console()


def pagerank_managers(conn: Neo4jConnection, top_n: int = 15) -> list[dict]:
    """Run PageRank on the REPORTS_TO network to identify influential managers.

    Uses Neo4j's native graph projection via GDS or falls back to APOC.
    """
    # Try APOC pageRank (available in community edition)
    try:
        results = conn.run("""
            MATCH (e:Employee)-[:REPORTS_TO]->(m:Employee)
            WITH COLLECT(DISTINCT e) + COLLECT(DISTINCT m) AS nodes,
                 COLLECT({source: e, target: m}) AS rels
            CALL apoc.algo.pageRank(nodes, rels) YIELD node, score
            WITH node, score
            ORDER BY score DESC
            LIMIT $top_n
            RETURN node.employee_id AS employee_id,
                   node.first_name + ' ' + node.last_name AS name,
                   node.job_level AS level,
                   node.department_id AS dept,
                   score
        """, top_n=top_n)
        return results
    except Exception:
        # Fallback: compute degree centrality manually
        return degree_centrality(conn, "REPORTS_TO", top_n)


def degree_centrality(conn: Neo4jConnection, rel_type: str = "REPORTS_TO",
                      top_n: int = 15) -> list[dict]:
    """Compute in-degree centrality (number of incoming relationships)."""
    results = conn.run(f"""
        MATCH (e:Employee)<-[r:{rel_type}]-(report:Employee)
        WITH e, COUNT(report) AS in_degree
        ORDER BY in_degree DESC
        LIMIT $top_n
        RETURN e.employee_id AS employee_id,
               e.first_name + ' ' + e.last_name AS name,
               e.job_level AS level,
               e.department_id AS dept,
               in_degree AS score
    """, top_n=top_n)
    return results


def betweenness_centrality(conn: Neo4jConnection, top_n: int = 15) -> list[dict]:
    """Find organizational bottlenecks via betweenness centrality.

    Uses APOC if available, otherwise falls back to degree centrality.
    """
    try:
        results = conn.run("""
            MATCH (e:Employee)-[:REPORTS_TO]->(m:Employee)
            WITH COLLECT(DISTINCT e) + COLLECT(DISTINCT m) AS nodes,
                 COLLECT({source: e, target: m}) AS rels
            CALL apoc.algo.betweenness(nodes, rels, 'BOTH') YIELD node, score
            WITH node, score
            WHERE score > 0
            ORDER BY score DESC
            LIMIT $top_n
            RETURN node.employee_id AS employee_id,
                   node.first_name + ' ' + node.last_name AS name,
                   node.job_level AS level,
                   node.department_id AS dept,
                   score
        """, top_n=top_n)
        return results
    except Exception:
        return degree_centrality(conn, "REPORTS_TO", top_n)


def span_of_control(conn: Neo4jConnection) -> list[dict]:
    """Analyze manager span of control across the org."""
    results = conn.run("""
        MATCH (manager:Employee)<-[:REPORTS_TO]-(report:Employee)
        WITH manager, COUNT(report) AS direct_reports
        RETURN manager.employee_id AS manager_id,
               manager.first_name + ' ' + manager.last_name AS name,
               manager.job_level AS level,
               manager.department_id AS dept,
               direct_reports
        ORDER BY direct_reports DESC
    """)
    return results


def print_centrality_report(conn: Neo4jConnection) -> None:
    """Print a full centrality analysis report."""
    console.print("\n[bold blue]Centrality Analysis[/bold blue]\n")

    # Degree centrality (most direct reports)
    console.print("[bold]Top Managers by Direct Reports:[/bold]")
    dc = degree_centrality(conn, "REPORTS_TO", 10)
    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Level")
    table.add_column("Dept")
    table.add_column("Direct Reports", justify="right", style="green")
    for r in dc:
        table.add_row(r["name"], r["level"], r["dept"], str(int(r["score"])))
    console.print(table)

    # Span of control stats
    soc = span_of_control(conn)
    if soc:
        spans = [r["direct_reports"] for r in soc]
        avg_span = sum(spans) / len(spans) if spans else 0
        console.print(f"\n[bold]Span of Control:[/bold]")
        console.print(f"  Avg: {avg_span:.1f} | Min: {min(spans)} | Max: {max(spans)} | Managers: {len(spans)}")


if __name__ == "__main__":
    conn = Neo4jConnection()
    if conn.verify():
        print_centrality_report(conn)
    conn.close()

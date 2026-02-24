"""Generate interactive HTML graph visualizations using Pyvis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyvis.network import Network
from rich.console import Console

from config.settings import EXPORTS_DIR
from phase4_graph.loader.neo4j_connection import Neo4jConnection
from phase4_graph.visualization.style_config import node_color, node_size, edge_color, risk_color

console = Console()


def _save_graph(net: Network, filename: str) -> str:
    """Save a Pyvis network to an HTML file and return the path."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORTS_DIR / filename
    net.write_html(str(path))
    console.print(f"  [green]Saved: {path}[/green]")
    return str(path)


def render_org_chart(conn: Neo4jConnection, max_depth: int = 3) -> str:
    """Render the organizational hierarchy as an interactive graph.

    Color-coded by department, sized by span of control.
    """
    console.print("\n[bold]Generating org chart...[/bold]")

    # Get employees and reporting relationships
    nodes_data = conn.run("""
        MATCH (e:Employee)
        WHERE e.status = 'Active'
        OPTIONAL MATCH (report:Employee)-[:REPORTS_TO]->(e)
        WITH e, COUNT(report) AS direct_reports
        RETURN e.employee_id AS id,
               e.first_name + ' ' + e.last_name AS name,
               e.job_level AS level,
               e.department_id AS dept,
               direct_reports
    """)

    edges_data = conn.run("""
        MATCH (e:Employee)-[:REPORTS_TO]->(m:Employee)
        WHERE e.status = 'Active' AND m.status = 'Active'
        RETURN e.employee_id AS source, m.employee_id AS target
    """)

    net = Network(height="800px", width="100%", directed=True,
                  bgcolor="#222222", font_color="white")
    net.barnes_hut(gravity=-3000, central_gravity=0.3)

    for node in nodes_data:
        size = 10 + node["direct_reports"] * 5
        color = node_color("Employee")
        title = f"{node['name']}\n{node['level']} | {node['dept']}\nDirect reports: {node['direct_reports']}"
        label = node["name"] if node["direct_reports"] > 0 or node["level"] in ("VP", "CX") else ""
        net.add_node(node["id"], label=label, title=title, color=color, size=size)

    for edge in edges_data:
        net.add_edge(edge["source"], edge["target"], color="#666666")

    return _save_graph(net, "org_chart.html")


def render_department_network(conn: Neo4jConnection) -> str:
    """Render departments and their divisions as a network."""
    console.print("\n[bold]Generating department network...[/bold]")

    dept_data = conn.run("""
        MATCH (d:Department)-[:PART_OF]->(div:Division)
        OPTIONAL MATCH (e:Employee)-[:BELONGS_TO]->(d)
        WHERE e.status = 'Active'
        WITH d, div, COUNT(e) AS headcount
        RETURN d.dept_id AS dept_id, d.name AS dept_name,
               div.division_id AS div_id, div.name AS div_name,
               headcount
    """)

    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.barnes_hut(gravity=-5000)

    divisions_added = set()
    for row in dept_data:
        if row["div_id"] not in divisions_added:
            net.add_node(row["div_id"], label=row["div_name"],
                        color=node_color("Division"), size=40, shape="box")
            divisions_added.add(row["div_id"])

        net.add_node(row["dept_id"], label=f"{row['dept_name']}\n({row['headcount']})",
                    color=node_color("Department"), size=15 + row["headcount"] // 3)
        net.add_edge(row["dept_id"], row["div_id"], color="#888888")

    return _save_graph(net, "department_network.html")


def render_compensation_map(conn: Neo4jConnection) -> str:
    """Render employees connected to salary bands, colored by compa-ratio."""
    console.print("\n[bold]Generating compensation map...[/bold]")

    data = conn.run("""
        MATCH (e:Employee)-[:HOLDS_POSITION]->(p:Position)-[:IN_SALARY_BAND]->(b:SalaryBand)
        MATCH (e)-[:EARNS_BASE]->(s:BaseSalary)
        WHERE e.status = 'Active'
        WITH e, p, b, s
        ORDER BY s.effective_date DESC
        WITH e, p, b, COLLECT(s)[0] AS latest_sal
        WITH e, p, b, latest_sal,
             CASE WHEN b.midpoint > 0
                  THEN toFloat(latest_sal.amount) / toFloat(b.midpoint) * 100
                  ELSE 100 END AS compa_ratio
        RETURN e.employee_id AS emp_id,
               e.first_name + ' ' + e.last_name AS name,
               e.job_level AS level,
               e.gender AS gender,
               b.band_id AS band_id,
               b.job_family + ' / ' + b.job_level AS band_label,
               b.midpoint AS midpoint,
               latest_sal.amount AS salary,
               compa_ratio
        LIMIT 200
    """)

    net = Network(height="700px", width="100%", bgcolor="#222222", font_color="white")
    net.barnes_hut(gravity=-2000)

    bands_added = set()
    for row in data:
        # Color employee by compa-ratio
        cr = row["compa_ratio"] or 100
        if cr >= 110:
            emp_color = "#27AE60"  # Green - above band
        elif cr >= 95:
            emp_color = "#3498DB"  # Blue - at band
        elif cr >= 85:
            emp_color = "#F39C12"  # Yellow - below band
        else:
            emp_color = "#E74C3C"  # Red - well below band

        title = f"{row['name']}\n{row['level']} | {row['gender']}\nSalary: ${row['salary']:,.0f}\nCompa-ratio: {cr:.0f}%"
        net.add_node(f"emp_{row['emp_id']}", label=row['name'], title=title,
                    color=emp_color, size=15)

        if row["band_id"] not in bands_added:
            net.add_node(f"band_{row['band_id']}",
                        label=f"{row['band_label']}\n${row['midpoint']:,.0f}",
                        color=node_color("SalaryBand"), size=30, shape="box")
            bands_added.add(row["band_id"])

        net.add_edge(f"emp_{row['emp_id']}", f"band_{row['band_id']}", color="#555555")

    return _save_graph(net, "compensation_map.html")


def render_recruiting_funnel(conn: Neo4jConnection) -> str:
    """Render the recruiting pipeline: sources -> candidates -> hires -> performance."""
    console.print("\n[bold]Generating recruiting funnel...[/bold]")

    data = conn.run("""
        MATCH (sc:SourceChannel)<-[:SOURCED_FROM]-(c:Candidate)
        MATCH (c)-[:HAS_APPLICATION]->(app:Application)
        WITH sc, c, app, app.status AS app_status
        RETURN sc.channel_name AS source,
               app_status AS status,
               COUNT(*) AS count
        ORDER BY source, count DESC
    """)

    net = Network(height="600px", width="100%", directed=True,
                  bgcolor="#222222", font_color="white")
    net.barnes_hut(gravity=-3000)

    sources = set()
    statuses = set()
    for row in data:
        src = row["source"]
        status = row["status"]

        if src not in sources:
            net.add_node(f"src_{src}", label=src, color=node_color("SourceChannel"),
                        size=30, shape="box")
            sources.add(src)

        if status not in statuses:
            color = "#27AE60" if status == "Hired" else "#E74C3C" if status == "Rejected" else "#F39C12"
            net.add_node(f"status_{status}", label=status, color=color,
                        size=25, shape="box")
            statuses.add(status)

        width = max(1, row["count"] // 20)
        net.add_edge(f"src_{src}", f"status_{status}",
                    value=row["count"], title=str(row["count"]),
                    color="#666666", width=width)

    return _save_graph(net, "recruiting_funnel.html")


def render_skills_network(conn: Neo4jConnection, min_shared: int = 1) -> str:
    """Render employees connected through shared skills."""
    console.print("\n[bold]Generating skills network...[/bold]")

    # Get skills and their employees
    data = conn.run("""
        MATCH (e:Employee)-[h:HAS_SKILL]->(s:Skill)
        WHERE e.status = 'Active'
        RETURN e.employee_id AS emp_id,
               e.first_name + ' ' + e.last_name AS name,
               e.department_id AS dept,
               s.skill_id AS skill_id,
               s.name AS skill_name,
               s.category AS category
        LIMIT 500
    """)

    net = Network(height="700px", width="100%", bgcolor="#222222", font_color="white")
    net.barnes_hut(gravity=-2000)

    emps_added = set()
    skills_added = set()

    for row in data:
        if row["emp_id"] not in emps_added:
            net.add_node(f"emp_{row['emp_id']}", label=row["name"],
                        title=f"{row['name']}\n{row['dept']}",
                        color=node_color("Employee"), size=12)
            emps_added.add(row["emp_id"])

        if row["skill_id"] not in skills_added:
            net.add_node(f"skill_{row['skill_id']}", label=row["skill_name"],
                        title=f"{row['skill_name']} ({row['category']})",
                        color=node_color("Skill"), size=25, shape="diamond")
            skills_added.add(row["skill_id"])

        net.add_edge(f"emp_{row['emp_id']}", f"skill_{row['skill_id']}", color="#444444")

    return _save_graph(net, "skills_network.html")


def render_all(conn: Neo4jConnection) -> list[str]:
    """Generate all visualizations and return list of file paths."""
    console.print("\n[bold blue]Generating all visualizations...[/bold blue]")

    paths = [
        render_org_chart(conn),
        render_department_network(conn),
        render_compensation_map(conn),
        render_recruiting_funnel(conn),
        render_skills_network(conn),
    ]

    console.print(f"\n[green]Generated {len(paths)} visualizations in data/exports/[/green]")
    return paths


if __name__ == "__main__":
    conn = Neo4jConnection()
    if conn.verify():
        render_all(conn)
    conn.close()

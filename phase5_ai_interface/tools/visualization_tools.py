"""Generate graph visualizations from Cypher queries."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from pyvis.network import Network

from config.settings import EXPORTS_DIR
from phase4_graph.loader.neo4j_connection import Neo4jConnection
from phase4_graph.visualization.style_config import node_color
from phase4_graph.visualization.pyvis_renderer import (
    render_org_chart, render_department_network, render_compensation_map,
    render_recruiting_funnel, render_skills_network,
)

_conn = None


def _get_conn() -> Neo4jConnection:
    global _conn
    if _conn is None:
        _conn = Neo4jConnection()
        _conn.verify()
    return _conn


def visualize_subgraph(cypher: str, title: str = "subgraph") -> str:
    """Execute a Cypher query and render the results as an interactive HTML graph.

    The Cypher query should return paths, nodes, or relationships.
    For best results, return nodes with their properties.

    Args:
        cypher: Cypher query that returns graph data (nodes/relationships).
        title: Title for the visualization file.

    Returns:
        JSON with the file path to the generated HTML visualization.
    """
    try:
        conn = _get_conn()
        results = conn.run(cypher)

        if not results:
            return json.dumps({"error": "Query returned no results"})

        net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
        net.barnes_hut(gravity=-3000)

        nodes_added = set()
        for row in results:
            for key, val in row.items():
                if isinstance(val, dict) and "id" in str(val):
                    continue
                if isinstance(val, str):
                    node_id = val
                    if node_id not in nodes_added:
                        net.add_node(node_id, label=str(val)[:30], title=str(val))
                        nodes_added.add(node_id)

        # For simple tabular results, create a node-per-row visualization
        if not nodes_added:
            for i, row in enumerate(results[:100]):
                label = " | ".join(str(v)[:20] for v in row.values() if v)
                net.add_node(i, label=label[:40], title=json.dumps(row, default=str))

        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c for c in title if c.isalnum() or c in "-_").lower()
        filename = f"custom_{safe_title}.html"
        path = EXPORTS_DIR / filename
        net.write_html(str(path))

        return json.dumps({"file": str(path), "node_count": len(nodes_added) or len(results)})

    except Exception as e:
        return json.dumps({"error": str(e)})


def run_graph_algorithm(algorithm: str, **kwargs) -> str:
    """Run a graph algorithm and return results.

    Args:
        algorithm: Algorithm to run. Options:
            - "centrality": Top managers by degree centrality
            - "community": Cross-department clusters and skill communities
            - "cascade": Impact analysis if an employee departs (requires employee_id)
            - "org_distance": Shortest path between two employees (requires emp1_id, emp2_id)
            - "flight_risk": Top flight risks by organizational impact
            - "render_org_chart": Generate org chart visualization
            - "render_department_network": Generate department network
            - "render_compensation_map": Generate compensation map
            - "render_recruiting_funnel": Generate recruiting funnel
            - "render_skills_network": Generate skills network

    Returns:
        JSON string with algorithm results.
    """
    try:
        conn = _get_conn()

        if algorithm == "centrality":
            from phase4_graph.analytics.centrality import degree_centrality, span_of_control
            dc = degree_centrality(conn, "REPORTS_TO", kwargs.get("top_n", 15))
            soc = span_of_control(conn)
            spans = [r["direct_reports"] for r in soc] if soc else []
            return json.dumps({
                "top_by_degree": dc,
                "span_stats": {
                    "avg": sum(spans) / len(spans) if spans else 0,
                    "min": min(spans) if spans else 0,
                    "max": max(spans) if spans else 0,
                    "manager_count": len(spans),
                }
            }, indent=2, default=str)

        elif algorithm == "community":
            from phase4_graph.analytics.community_detection import (
                department_clusters, skill_communities, department_diversity_profile
            )
            return json.dumps({
                "cross_dept_reporting": department_clusters(conn),
                "skill_communities": skill_communities(conn),
                "diversity_profile": department_diversity_profile(conn),
            }, indent=2, default=str)

        elif algorithm == "cascade":
            from phase4_graph.analytics.path_analysis import cascade_impact
            emp_id = kwargs.get("employee_id")
            if not emp_id:
                return json.dumps({"error": "employee_id is required for cascade analysis"})
            return json.dumps(cascade_impact(conn, emp_id), indent=2, default=str)

        elif algorithm == "org_distance":
            from phase4_graph.analytics.path_analysis import org_distance
            emp1 = kwargs.get("emp1_id")
            emp2 = kwargs.get("emp2_id")
            if not emp1 or not emp2:
                return json.dumps({"error": "emp1_id and emp2_id are required"})
            return json.dumps(org_distance(conn, emp1, emp2), indent=2, default=str)

        elif algorithm == "flight_risk":
            from phase4_graph.analytics.path_analysis import flight_risk_cascade
            return json.dumps(flight_risk_cascade(conn, kwargs.get("top_n", 15)),
                            indent=2, default=str)

        elif algorithm.startswith("render_"):
            render_funcs = {
                "render_org_chart": render_org_chart,
                "render_department_network": render_department_network,
                "render_compensation_map": render_compensation_map,
                "render_recruiting_funnel": render_recruiting_funnel,
                "render_skills_network": render_skills_network,
            }
            func = render_funcs.get(algorithm)
            if func:
                path = func(conn)
                return json.dumps({"file": path, "algorithm": algorithm})
            return json.dumps({"error": f"Unknown render: {algorithm}"})

        else:
            return json.dumps({
                "error": f"Unknown algorithm: {algorithm}",
                "available": ["centrality", "community", "cascade", "org_distance",
                            "flight_risk", "render_org_chart", "render_department_network",
                            "render_compensation_map", "render_recruiting_funnel",
                            "render_skills_network"]
            })

    except Exception as e:
        return json.dumps({"error": str(e)})

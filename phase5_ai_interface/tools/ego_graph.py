"""Build interactive Pyvis ego-graphs for individual employees."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyvis.network import Network

from config.settings import EXPORTS_DIR
from phase4_graph.loader.neo4j_connection import Neo4jConnection
from phase4_graph.visualization.style_config import (
    node_color, node_size, edge_color, NODE_COLORS,
)

_conn = None


def _get_conn() -> Neo4jConnection:
    global _conn
    if _conn is None:
        _conn = Neo4jConnection()
        _conn.verify()
    return _conn


def build_ego_graph(emp_id: str, hops: int = 1) -> str:
    """Build and save an interactive Pyvis ego-graph for an employee.

    Uses conn.run() directly (not query_graph) because we need native
    dicts/lists for node properties rather than stringified values.

    Args:
        emp_id: Employee ID (e.g. "EMP-00001")
        hops: Number of hops from center (1 or 2)

    Returns:
        Path to the saved HTML file.
    """
    conn = _get_conn()
    hops = max(1, min(hops, 2))

    # Fetch all nodes and edges within N hops of the employee
    data = conn.run("""
        MATCH (center:Employee {employee_id: $eid})
        CALL {
            WITH center
            MATCH path = (center)-[*1..%(hops)d]-(neighbor)
            UNWIND relationships(path) AS r
            WITH DISTINCT r,
                 startNode(r) AS src,
                 endNode(r) AS tgt
            RETURN src, tgt, r, type(r) AS rel_type
        }
        WITH center, collect({src: src, tgt: tgt, r: r, rel_type: rel_type}) AS edges
        RETURN center, edges
    """ % {"hops": hops}, eid=emp_id)

    if not data:
        return ""

    row = data[0]
    center = row["center"]
    edges = row["edges"]

    net = Network(
        height="600px",
        width="100%",
        bgcolor="#222222",
        font_color="white",
        directed=True,
    )
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    # Track added nodes to avoid duplicates
    added_nodes = set()

    def _node_label(node_dict: dict) -> str:
        """Pick the best display label for a node."""
        if "first_name" in node_dict and "last_name" in node_dict:
            return f"{node_dict['first_name']} {node_dict['last_name']}"
        for key in ("name", "title", "channel_name", "description", "cycle_id",
                     "review_id", "goal_id", "salary_id", "bonus_id", "grant_id",
                     "event_id", "band_id", "skill_id"):
            if key in node_dict and node_dict[key]:
                return str(node_dict[key])
        return str(node_dict.get("employee_id", ""))

    def _node_id(node_dict: dict) -> str:
        """Get a unique ID for a node."""
        for key in ("employee_id", "dept_id", "division_id", "location_id",
                     "position_id", "family_id", "level_id", "skill_id",
                     "req_id", "application_id", "interview_id", "offer_id",
                     "channel_name", "review_id", "goal_id", "cycle_id",
                     "band_id", "salary_id", "bonus_id", "grant_id",
                     "event_id", "candidate_id"):
            if key in node_dict and node_dict[key]:
                return str(node_dict[key])
        return str(id(node_dict))

    def _node_labels_from_dict(node_dict: dict) -> str:
        """Infer the Neo4j label from node properties."""
        # Map distinguishing property keys to labels
        key_to_label = {
            "employee_id": "Employee",
            "dept_id": "Department",
            "division_id": "Division",
            "location_id": "Location",
            "position_id": "Position",
            "family_id": "JobFamily",
            "level_id": "JobLevel",
            "skill_id": "Skill",
            "req_id": "Requisition",
            "application_id": "Application",
            "interview_id": "Interview",
            "offer_id": "Offer",
            "channel_name": "SourceChannel",
            "review_id": "PerformanceReview",
            "goal_id": "Goal",
            "cycle_id": "PerformanceCycle",
            "band_id": "SalaryBand",
            "salary_id": "BaseSalary",
            "bonus_id": "Bonus",
            "grant_id": "EquityGrant",
            "event_id": "TemporalEvent",
            "candidate_id": "Candidate",
        }
        for key, label in key_to_label.items():
            if key in node_dict:
                return label
        return "Unknown"

    def _tooltip(node_dict: dict) -> str:
        """Build HTML tooltip showing all properties."""
        lines = []
        for k, v in node_dict.items():
            if v is not None:
                lines.append(f"<b>{k}</b>: {v}")
        return "<br>".join(lines)

    def _add_node(node_dict: dict, is_center: bool = False):
        """Add a node to the network if not already present."""
        nid = _node_id(node_dict)
        if nid in added_nodes:
            return nid
        added_nodes.add(nid)

        label_type = _node_labels_from_dict(node_dict)
        color = node_color(label_type)
        size = node_size(label_type)

        if is_center:
            size = size * 2
            border_width = 3
            border_color = "#FFFFFF"
        else:
            border_width = 1
            border_color = color

        net.add_node(
            nid,
            label=_node_label(node_dict),
            title=_tooltip(node_dict),
            color={
                "background": color,
                "border": border_color,
                "highlight": {"background": color, "border": "#FFFFFF"},
            },
            size=size,
            borderWidth=border_width,
        )
        return nid

    # Add center node
    _add_node(center, is_center=True)

    # Add edges and neighbor nodes
    for edge_data in edges:
        src_dict = edge_data["src"]
        tgt_dict = edge_data["tgt"]
        rel_type = edge_data["rel_type"]

        src_id = _add_node(src_dict)
        tgt_id = _add_node(tgt_dict)

        # Build edge tooltip from relationship properties
        rel_props = edge_data.get("r", {})
        edge_title = rel_type
        if isinstance(rel_props, dict):
            prop_lines = [f"<b>{rel_type}</b>"]
            for k, v in rel_props.items():
                if v is not None and k not in ("_id", "_start", "_end"):
                    prop_lines.append(f"{k}: {v}")
            edge_title = "<br>".join(prop_lines)

        net.add_edge(
            src_id,
            tgt_id,
            label=rel_type,
            title=edge_title,
            color=edge_color(rel_type),
            font={"size": 8, "color": "#999999"},
        )

    # Save
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"ego_graph_{emp_id}.html"
    path = EXPORTS_DIR / filename
    net.write_html(str(path))
    return str(path)

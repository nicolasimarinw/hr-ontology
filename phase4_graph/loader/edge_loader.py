"""Load relationships from Parquet data lake into Neo4j."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import math
import duckdb
import pandas as pd
from rich.console import Console

from config.settings import LAKE_DATA_DIR
from phase3_ontology.mapping import EDGE_MAPPINGS, NODE_MAPPINGS
from phase4_graph.loader.neo4j_connection import Neo4jConnection

console = Console()


def _clean_value(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return str(v.date()) if not pd.isna(v) else None
    if hasattr(v, 'item'):
        return v.item()
    if isinstance(v, str) and v in ('nan', 'None', 'NaT'):
        return None
    return v


def _get_id_property(label: str) -> str:
    """Look up the ID property for a node label from NODE_MAPPINGS."""
    label_to_id = {
        "Employee": "employee_id",
        "Candidate": "candidate_id",
        "Department": "dept_id",
        "Division": "division_id",
        "Location": "location_id",
        "Position": "position_id",
        "JobFamily": "family_id",
        "JobLevel": "level_id",
        "Skill": "skill_id",
        "Requisition": "req_id",
        "Application": "application_id",
        "Interview": "interview_id",
        "Offer": "offer_id",
        "PerformanceReview": "review_id",
        "Goal": "goal_id",
        "SalaryBand": "band_id",
        "BaseSalary": "salary_id",
        "Bonus": "bonus_id",
        "EquityGrant": "grant_id",
        "PerformanceCycle": "cycle_id",
        "SourceChannel": "channel_name",
        "TemporalEvent": "event_id",
    }
    return label_to_id.get(label, "id")


def load_all_edges(conn: Neo4jConnection) -> dict[str, int]:
    """Load all relationship types from the data lake into Neo4j.

    Returns dict of rel_type -> count loaded.
    """
    console.print("\n[bold blue]Loading relationships into Neo4j...[/bold blue]\n")

    con = duckdb.connect()
    results = {}

    for mapping in EDGE_MAPPINGS:
        rel_type = mapping["type"]
        source_table = mapping["source_table"]
        source_id_col = mapping["source_id"]
        source_label = mapping["source_label"]
        target_label = mapping["target_label"]
        filter_clause = mapping.get("filter")
        edge_props = mapping.get("edge_properties", {})

        # Handle join-based mappings (IN_SALARY_BAND) first
        if "join" in mapping:
            count = _load_salary_band_edges(conn, con, mapping)
            results[rel_type] = count
            console.print(f"  [green]{rel_type}[/green]: {count} relationships")
            continue

        target_id_col = mapping["target_id"]

        # Handle temporal event edges (need special handling)
        if target_id_col == "__row_index__":
            count = _load_temporal_event_edges(conn, con, mapping)
            results[rel_type] = count
            console.print(f"  [green]{rel_type}[/green]: {count} relationships")
            continue

        parquet_path = LAKE_DATA_DIR / f"{source_table}.parquet"
        if not parquet_path.exists():
            console.print(f"  [yellow]SKIP: {parquet_path} not found[/yellow]")
            continue

        # Read data
        query = f"SELECT * FROM '{parquet_path}'"
        if filter_clause:
            query += f" WHERE {filter_clause}"
        df = con.execute(query).fetchdf()

        # Build edge rows
        source_id_prop = _get_id_property(source_label)
        target_id_prop = _get_id_property(target_label)

        rows = []
        for _, record in df.iterrows():
            src_val = _clean_value(record.get(source_id_col))
            tgt_val = _clean_value(record.get(target_id_col))

            if src_val is None or tgt_val is None:
                continue

            row = {"source_id": str(src_val), "target_id": str(tgt_val)}

            # Add edge properties if specified
            for neo_prop, src_field in edge_props.items():
                row[neo_prop] = _clean_value(record.get(src_field))

            rows.append(row)

        if not rows:
            results[rel_type] = 0
            console.print(f"  [dim]{rel_type}[/dim]: 0 relationships (no data)")
            continue

        # Build MERGE Cypher
        prop_set = ""
        if edge_props:
            set_parts = [f"r.{prop} = row.{prop}" for prop in edge_props.keys()]
            prop_set = f"SET {', '.join(set_parts)}"

        cypher = f"""
        UNWIND $batch AS row
        MATCH (a:{source_label} {{{source_id_prop}: row.source_id}})
        MATCH (b:{target_label} {{{target_id_prop}: row.target_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        {prop_set}
        """

        count = conn.run_batch(cypher, rows, batch_size=500)
        results[rel_type] = count
        console.print(f"  [green]{rel_type}[/green]: {count} relationships")

    con.close()
    return results


def _load_salary_band_edges(conn: Neo4jConnection, con, mapping: dict) -> int:
    """Load Position -[:IN_SALARY_BAND]-> SalaryBand via job_family+job_level join."""
    positions_path = LAKE_DATA_DIR / "hris/positions.parquet"
    bands_path = LAKE_DATA_DIR / "compensation/salary_bands.parquet"

    if not positions_path.exists() or not bands_path.exists():
        return 0

    df = con.execute(f"""
        SELECT p.position_id, b.band_id
        FROM '{positions_path}' p
        JOIN '{bands_path}' b ON p.job_family = b.job_family AND p.job_level = b.job_level
    """).fetchdf()

    rows = [{"source_id": str(row["position_id"]), "target_id": str(row["band_id"])}
            for _, row in df.iterrows()]

    cypher = """
    UNWIND $batch AS row
    MATCH (p:Position {position_id: row.source_id})
    MATCH (b:SalaryBand {band_id: row.target_id})
    MERGE (p)-[:IN_SALARY_BAND]->(b)
    """
    return conn.run_batch(cypher, rows, batch_size=500)


def _load_temporal_event_edges(conn: Neo4jConnection, con, mapping: dict) -> int:
    """Load Employee -[:EXPERIENCED_EVENT]-> TemporalEvent."""
    parquet_path = LAKE_DATA_DIR / "hris/employment_history.parquet"
    if not parquet_path.exists():
        return 0

    df = con.execute(f"SELECT * FROM '{parquet_path}'").fetchdf()

    rows = [{"source_id": str(row["employee_id"]), "target_id": f"EVT-{idx+1:06d}"}
            for idx, row in df.iterrows()]

    cypher = """
    UNWIND $batch AS row
    MATCH (e:Employee {employee_id: row.source_id})
    MATCH (evt:TemporalEvent {event_id: row.target_id})
    MERGE (e)-[:EXPERIENCED_EVENT]->(evt)
    """
    return conn.run_batch(cypher, rows, batch_size=500)

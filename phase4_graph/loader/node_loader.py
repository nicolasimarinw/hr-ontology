"""Load nodes from Parquet data lake into Neo4j."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import math
import duckdb
import pandas as pd
from rich.console import Console

from config.settings import LAKE_DATA_DIR
from config.company_profile import SKILL_CATALOG
from phase3_ontology.mapping import NODE_MAPPINGS
from phase4_graph.loader.neo4j_connection import Neo4jConnection

console = Console()


def _clean_value(v):
    """Convert pandas/numpy types to Neo4j-compatible Python types."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return str(v.date()) if not pd.isna(v) else None
    if hasattr(v, 'item'):  # numpy scalar
        return v.item()
    if isinstance(v, str) and v in ('nan', 'None', 'NaT'):
        return None
    return v


def _clean_row(row: dict) -> dict:
    """Clean all values in a row dict."""
    return {k: _clean_value(v) for k, v in row.items() if _clean_value(v) is not None}


def load_all_nodes(conn: Neo4jConnection) -> dict[str, int]:
    """Load all node types from the data lake into Neo4j.

    Returns dict of label -> count loaded.
    """
    console.print("\n[bold blue]Loading nodes into Neo4j...[/bold blue]\n")

    con = duckdb.connect()
    results = {}

    for mapping in NODE_MAPPINGS:
        label = mapping["label"]
        source = mapping["source"]
        props = mapping["properties"]
        id_field = mapping["id_field"]

        # Special case: skill catalog is not in Parquet
        if source == "__skill_catalog__":
            rows = []
            for skill in SKILL_CATALOG:
                row = {}
                for neo_prop, src_field in props.items():
                    row[neo_prop] = skill.get(src_field)
                rows.append(row)

        # Special case: auto-generated IDs for employment history
        elif id_field == "__row_index__":
            prefix = mapping.get("auto_id_prefix", "ROW")
            parquet_path = LAKE_DATA_DIR / f"{source}.parquet"
            if not parquet_path.exists():
                console.print(f"  [yellow]SKIP: {parquet_path} not found[/yellow]")
                continue
            df = con.execute(f"SELECT * FROM '{parquet_path}'").fetchdf()
            rows = []
            for idx, record in df.iterrows():
                row = {"event_id": f"{prefix}-{idx+1:06d}"}
                for neo_prop, src_field in props.items():
                    row[neo_prop] = record.get(src_field)
                rows.append(_clean_row(row))

        else:
            parquet_path = LAKE_DATA_DIR / f"{source}.parquet"
            if not parquet_path.exists():
                console.print(f"  [yellow]SKIP: {parquet_path} not found[/yellow]")
                continue

            df = con.execute(f"SELECT * FROM '{parquet_path}'").fetchdf()

            # Handle deduplication
            dedup_col = mapping.get("deduplicate_on")
            if dedup_col:
                df = df.drop_duplicates(subset=[dedup_col])

            rows = []
            for _, record in df.iterrows():
                row = {}
                for neo_prop, src_field in props.items():
                    row[neo_prop] = record.get(src_field)
                rows.append(_clean_row(row))

        if not rows:
            continue

        # Build MERGE statement
        # Use the first property as the merge key (the ID)
        id_prop = list(props.keys())[0]
        if id_field == "__row_index__":
            id_prop = "event_id"

        set_clauses = []
        for prop_name in rows[0].keys():
            if prop_name != id_prop:
                set_clauses.append(f"n.{prop_name} = row.{prop_name}")

        set_str = ", ".join(set_clauses) if set_clauses else ""
        set_line = f"SET {set_str}" if set_str else ""

        cypher = f"""
        UNWIND $batch AS row
        MERGE (n:{label} {{{id_prop}: row.{id_prop}}})
        {set_line}
        """

        count = conn.run_batch(cypher, rows, batch_size=500)
        results[label] = count
        console.print(f"  [green]{label}[/green]: {count} nodes")

    con.close()
    return results

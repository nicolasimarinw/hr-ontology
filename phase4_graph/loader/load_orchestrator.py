"""Full graph load pipeline: clear -> constrain -> load nodes -> load edges -> validate."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from phase3_ontology.constraints import generate_constraint_statements
from phase4_graph.loader.neo4j_connection import Neo4jConnection
from phase4_graph.loader.node_loader import load_all_nodes
from phase4_graph.loader.edge_loader import load_all_edges

console = Console()


def run_load_pipeline() -> bool:
    """Execute the full graph load pipeline."""
    console.print(Panel.fit(
        "[bold green]Phase 4: Graph Construction[/bold green]\n"
        "Loading HR ontology into Neo4j",
        title="HR Ontology",
    ))

    # 1. Connect
    conn = Neo4jConnection()
    if not conn.verify():
        console.print("[red]Cannot connect to Neo4j. Is Docker running?[/red]")
        console.print("Run: docker compose up -d")
        return False

    # 2. Clear database
    console.print("\n[yellow]Step 1: Clearing database...[/yellow]")
    conn.clear_database()

    # 3. Apply constraints and indexes
    console.print("\n[yellow]Step 2: Applying constraints and indexes...[/yellow]")
    statements = generate_constraint_statements()
    for stmt in statements:
        try:
            conn.run(stmt)
        except Exception as e:
            # Some constraints may already exist, that's fine
            if "already exists" not in str(e).lower():
                console.print(f"  [red]Warning: {e}[/red]")
    console.print(f"  Applied {len(statements)} constraints/indexes")

    # 4. Load nodes
    console.print("\n[yellow]Step 3: Loading nodes...[/yellow]")
    node_counts = load_all_nodes(conn)

    # 5. Load edges
    console.print("\n[yellow]Step 4: Loading relationships...[/yellow]")
    edge_counts = load_all_edges(conn)

    # 6. Validate
    console.print("\n[yellow]Step 5: Validating...[/yellow]")
    total_nodes = conn.count_nodes()
    total_rels = conn.count_relationships()

    # Print summary
    node_table = Table(title="Nodes Loaded")
    node_table.add_column("Label", style="cyan")
    node_table.add_column("Count", justify="right", style="green")
    for label, count in sorted(node_counts.items()):
        node_table.add_row(label, str(count))
    node_table.add_row("[bold]TOTAL[/bold]", f"[bold]{total_nodes}[/bold]")
    console.print(node_table)

    edge_table = Table(title="Relationships Loaded")
    edge_table.add_column("Type", style="cyan")
    edge_table.add_column("Count", justify="right", style="green")
    for rel_type, count in sorted(edge_counts.items()):
        edge_table.add_row(rel_type, str(count))
    edge_table.add_row("[bold]TOTAL[/bold]", f"[bold]{total_rels}[/bold]")
    console.print(edge_table)

    console.print(Panel.fit(
        f"[bold green]Graph loaded successfully![/bold green]\n\n"
        f"Total nodes:         {total_nodes:,}\n"
        f"Total relationships: {total_rels:,}\n"
        f"Node types:          {len(node_counts)}\n"
        f"Relationship types:  {len(edge_counts)}",
        title="Summary",
    ))

    conn.close()
    return True


if __name__ == "__main__":
    success = run_load_pipeline()
    sys.exit(0 if success else 1)

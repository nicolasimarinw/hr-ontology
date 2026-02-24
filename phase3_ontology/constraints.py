"""Neo4j constraints and indexes generated from the property graph schema."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console

from phase3_ontology.schema import ALL_NODE_SCHEMAS

console = Console()


def generate_constraint_statements() -> list[str]:
    """Generate Cypher statements for uniqueness constraints and indexes."""
    statements = []

    for name, schema in ALL_NODE_SCHEMAS.items():
        primary_label = schema.labels[-1]  # Most specific label
        id_prop = schema.id_property

        # Uniqueness constraint on the ID property
        constraint_name = f"uniq_{primary_label.lower()}_{id_prop}"
        statements.append(
            f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
            f"FOR (n:{primary_label}) REQUIRE n.{id_prop} IS UNIQUE"
        )

        # Additional indexes on frequently queried properties
        for idx_prop in schema.indexes:
            if idx_prop == id_prop:
                continue  # Already covered by uniqueness constraint
            idx_name = f"idx_{primary_label.lower()}_{idx_prop}"
            statements.append(
                f"CREATE INDEX {idx_name} IF NOT EXISTS "
                f"FOR (n:{primary_label}) ON (n.{idx_prop})"
            )

    # Composite indexes for common query patterns
    statements.append(
        "CREATE INDEX idx_employee_dept_level IF NOT EXISTS "
        "FOR (n:Employee) ON (n.department_id, n.job_level)"
    )
    statements.append(
        "CREATE INDEX idx_employee_status IF NOT EXISTS "
        "FOR (n:Employee) ON (n.status)"
    )
    statements.append(
        "CREATE INDEX idx_employee_gender IF NOT EXISTS "
        "FOR (n:Employee) ON (n.gender)"
    )
    statements.append(
        "CREATE INDEX idx_employee_ethnicity IF NOT EXISTS "
        "FOR (n:Employee) ON (n.ethnicity)"
    )

    return statements


def print_constraints() -> None:
    """Print all constraint and index statements."""
    statements = generate_constraint_statements()
    console.print(f"\n[bold blue]Neo4j Constraints & Indexes ({len(statements)} statements)[/bold blue]\n")
    for stmt in statements:
        console.print(f"  [cyan]{stmt}[/cyan]")


if __name__ == "__main__":
    print_constraints()

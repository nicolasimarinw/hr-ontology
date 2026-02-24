"""Auto-generates a catalog of all Parquet tables with columns, types, PKs, and FKs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb
from rich.console import Console
from rich.table import Table

from config.settings import LAKE_DATA_DIR

console = Console()

# Primary keys and foreign keys for each table
TABLE_KEYS = {
    "hris/employees": {
        "pk": "employee_id",
        "fks": {
            "manager_id": "hris/employees.employee_id",
            "department_id": "hris/departments.dept_id",
            "position_id": "hris/positions.position_id",
            "location_id": "hris/locations.id",
        },
    },
    "hris/departments": {
        "pk": "dept_id",
        "fks": {"head_id": "hris/employees.employee_id"},
    },
    "hris/positions": {
        "pk": "position_id",
        "fks": {"department_id": "hris/departments.dept_id"},
    },
    "hris/locations": {"pk": "id", "fks": {}},
    "hris/employment_history": {
        "pk": None,
        "fks": {"employee_id": "hris/employees.employee_id"},
    },
    "compensation/salary_bands": {"pk": "band_id", "fks": {}},
    "compensation/base_salary": {
        "pk": "salary_id",
        "fks": {"employee_id": "hris/employees.employee_id"},
    },
    "compensation/bonuses": {
        "pk": "bonus_id",
        "fks": {"employee_id": "hris/employees.employee_id"},
    },
    "compensation/equity_grants": {
        "pk": "grant_id",
        "fks": {"employee_id": "hris/employees.employee_id"},
    },
    "ats/requisitions": {
        "pk": "req_id",
        "fks": {
            "department_id": "hris/departments.dept_id",
            "hiring_manager_id": "hris/employees.employee_id",
        },
    },
    "ats/candidates": {"pk": "candidate_id", "fks": {}},
    "ats/applications": {
        "pk": "application_id",
        "fks": {
            "candidate_id": "ats/candidates.candidate_id",
            "req_id": "ats/requisitions.req_id",
        },
    },
    "ats/interviews": {
        "pk": "interview_id",
        "fks": {
            "application_id": "ats/applications.application_id",
            "interviewer_id": "hris/employees.employee_id",
        },
    },
    "ats/offers": {
        "pk": "offer_id",
        "fks": {"application_id": "ats/applications.application_id"},
    },
    "performance/performance_cycles": {"pk": "cycle_id", "fks": {}},
    "performance/goals": {
        "pk": "goal_id",
        "fks": {
            "employee_id": "hris/employees.employee_id",
            "cycle_id": "performance/performance_cycles.cycle_id",
        },
    },
    "performance/performance_reviews": {
        "pk": "review_id",
        "fks": {
            "employee_id": "hris/employees.employee_id",
            "reviewer_id": "hris/employees.employee_id",
            "cycle_id": "performance/performance_cycles.cycle_id",
        },
    },
    "performance/competency_assessments": {
        "pk": "assessment_id",
        "fks": {
            "employee_id": "hris/employees.employee_id",
            "cycle_id": "performance/performance_cycles.cycle_id",
        },
    },
}


def generate_registry() -> dict:
    """Introspect all Parquet files and produce a schema catalog."""
    console.print("\n[bold blue]Schema Registry[/bold blue]\n")

    con = duckdb.connect()
    registry = {}

    for table_path, keys in TABLE_KEYS.items():
        parquet_file = LAKE_DATA_DIR / f"{table_path}.parquet"
        if not parquet_file.exists():
            continue

        # Get schema info from DuckDB
        result = con.execute(
            f"DESCRIBE SELECT * FROM '{parquet_file}'"
        ).fetchall()

        columns = []
        for row in result:
            col_name = row[0]
            col_type = row[1]
            is_pk = col_name == keys.get("pk")
            fk_ref = keys.get("fks", {}).get(col_name)

            columns.append({
                "name": col_name,
                "type": col_type,
                "is_pk": is_pk,
                "fk_ref": fk_ref,
            })

        # Row count
        count = con.execute(
            f"SELECT COUNT(*) FROM '{parquet_file}'"
        ).fetchone()[0]

        registry[table_path] = {
            "columns": columns,
            "row_count": count,
            "pk": keys.get("pk"),
            "fks": keys.get("fks", {}),
        }

    con.close()

    # Print summary
    for table_name, info in sorted(registry.items()):
        table = Table(title=f"{table_name} ({info['row_count']} rows)")
        table.add_column("Column", style="cyan")
        table.add_column("Type")
        table.add_column("Key", style="yellow")

        for col in info["columns"]:
            key_str = ""
            if col["is_pk"]:
                key_str = "PK"
            elif col["fk_ref"]:
                key_str = f"FK -> {col['fk_ref']}"
            table.add_row(col["name"], col["type"], key_str)

        console.print(table)
        console.print()

    # Write markdown doc
    _write_markdown(registry)

    return registry


def _write_markdown(registry: dict) -> None:
    """Write schema catalog as Markdown."""
    md_path = LAKE_DATA_DIR / "schema_catalog.md"
    lines = ["# Data Lake Schema Catalog\n"]

    for table_name, info in sorted(registry.items()):
        lines.append(f"## {table_name}")
        lines.append(f"**Rows:** {info['row_count']}\n")
        lines.append("| Column | Type | Key |")
        lines.append("|--------|------|-----|")

        for col in info["columns"]:
            key = ""
            if col["is_pk"]:
                key = "PK"
            elif col["fk_ref"]:
                key = f"FK -> {col['fk_ref']}"
            lines.append(f"| {col['name']} | {col['type']} | {key} |")

        lines.append("")

    md_path.write_text("\n".join(lines))
    console.print(f"[green]Schema catalog written to {md_path}[/green]")


if __name__ == "__main__":
    generate_registry()

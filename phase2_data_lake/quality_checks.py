"""Referential integrity and data quality checks across all Parquet files."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb
from rich.console import Console
from rich.table import Table

from config.settings import LAKE_DATA_DIR
from phase2_data_lake.schema_registry import TABLE_KEYS

console = Console()


def run_quality_checks() -> tuple[int, int]:
    """Run all quality checks. Returns (passed_count, failed_count)."""
    console.print("\n[bold blue]Data Quality Checks[/bold blue]\n")

    con = duckdb.connect()
    passed = 0
    failed = 0
    results = []

    # 1. Foreign key integrity checks
    for table_path, keys in TABLE_KEYS.items():
        fks = keys.get("fks", {})
        source_file = LAKE_DATA_DIR / f"{table_path}.parquet"
        if not source_file.exists():
            continue

        for fk_col, ref_spec in fks.items():
            # Parse "hris/employees.employee_id" -> table path + column
            ref_table, ref_col = ref_spec.rsplit(".", 1)
            ref_file = LAKE_DATA_DIR / f"{ref_table}.parquet"

            if not ref_file.exists():
                results.append(("SKIP", f"{table_path}.{fk_col}", f"Ref table {ref_table} not found"))
                continue

            # Count orphaned references (non-null FK values not found in referenced table)
            query = f"""
                SELECT COUNT(*) FROM '{source_file}' s
                WHERE s."{fk_col}" IS NOT NULL
                  AND CAST(s."{fk_col}" AS VARCHAR) != 'nan'
                  AND CAST(s."{fk_col}" AS VARCHAR) NOT IN (
                    SELECT CAST(r."{ref_col}" AS VARCHAR) FROM '{ref_file}' r
                  )
            """
            try:
                orphan_count = con.execute(query).fetchone()[0]
            except Exception as e:
                results.append(("ERROR", f"{table_path}.{fk_col}", str(e)))
                failed += 1
                continue

            if orphan_count == 0:
                results.append(("PASS", f"{table_path}.{fk_col} -> {ref_spec}", "0 orphans"))
                passed += 1
            else:
                results.append(("FAIL", f"{table_path}.{fk_col} -> {ref_spec}", f"{orphan_count} orphans"))
                failed += 1

    # 2. Null rate checks on primary keys
    for table_path, keys in TABLE_KEYS.items():
        pk = keys.get("pk")
        if not pk:
            continue
        source_file = LAKE_DATA_DIR / f"{table_path}.parquet"
        if not source_file.exists():
            continue

        null_count = con.execute(
            f'SELECT COUNT(*) FROM \'{source_file}\' WHERE "{pk}" IS NULL'
        ).fetchone()[0]

        if null_count == 0:
            results.append(("PASS", f"{table_path}.{pk} NOT NULL", "0 nulls"))
            passed += 1
        else:
            results.append(("FAIL", f"{table_path}.{pk} NOT NULL", f"{null_count} nulls"))
            failed += 1

    # 3. Business rule checks
    emp_file = LAKE_DATA_DIR / "hris/employees.parquet"
    if emp_file.exists():
        # Termination date should be after hire date
        bad_terms = con.execute(f"""
            SELECT COUNT(*) FROM '{emp_file}'
            WHERE termination_date IS NOT NULL
              AND termination_date < hire_date
        """).fetchone()[0]

        if bad_terms == 0:
            results.append(("PASS", "employees: term_date >= hire_date", "All valid"))
            passed += 1
        else:
            results.append(("FAIL", "employees: term_date >= hire_date", f"{bad_terms} violations"))
            failed += 1

    # Salary should be positive
    sal_file = LAKE_DATA_DIR / "compensation/base_salary.parquet"
    if sal_file.exists():
        neg_sal = con.execute(f"""
            SELECT COUNT(*) FROM '{sal_file}' WHERE amount <= 0
        """).fetchone()[0]

        if neg_sal == 0:
            results.append(("PASS", "base_salary: amount > 0", "All positive"))
            passed += 1
        else:
            results.append(("FAIL", "base_salary: amount > 0", f"{neg_sal} non-positive"))
            failed += 1

    # Rating should be 1.0-5.0
    rev_file = LAKE_DATA_DIR / "performance/performance_reviews.parquet"
    if rev_file.exists():
        bad_ratings = con.execute(f"""
            SELECT COUNT(*) FROM '{rev_file}' WHERE rating < 1.0 OR rating > 5.0
        """).fetchone()[0]

        if bad_ratings == 0:
            results.append(("PASS", "reviews: rating in [1.0, 5.0]", "All valid"))
            passed += 1
        else:
            results.append(("FAIL", "reviews: rating in [1.0, 5.0]", f"{bad_ratings} out of range"))
            failed += 1

    con.close()

    # Print results
    table = Table(title="Quality Check Results")
    table.add_column("Status", style="bold")
    table.add_column("Check")
    table.add_column("Detail")

    for status, check, detail in results:
        style = {"PASS": "green", "FAIL": "red", "ERROR": "red", "SKIP": "yellow"}[status]
        table.add_row(f"[{style}]{status}[/{style}]", check, detail)

    console.print(table)
    console.print(f"\n[{'green' if failed == 0 else 'red'}]Passed: {passed} | Failed: {failed}[/]")

    return passed, failed


if __name__ == "__main__":
    p, f = run_quality_checks()
    sys.exit(0 if f == 0 else 1)

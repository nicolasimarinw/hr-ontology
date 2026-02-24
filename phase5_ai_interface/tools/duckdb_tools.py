"""Execute SQL queries against the DuckDB data lake."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import math
import duckdb
import pandas as pd

from config.settings import LAKE_DATA_DIR


def _clean_value(v):
    """Make a value JSON-serializable."""
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return str(v.date()) if not pd.isna(v) else None
    if hasattr(v, 'item'):
        return v.item()
    return v


def query_data_lake(sql: str) -> str:
    """Execute a SQL query against the Parquet-based data lake.

    The data lake is organized as:
    - data/lake/hris/ (employees, departments, positions, locations, employment_history)
    - data/lake/ats/ (requisitions, candidates, applications, interviews, offers)
    - data/lake/performance/ (performance_cycles, goals, performance_reviews, competency_assessments)
    - data/lake/compensation/ (salary_bands, base_salary, bonuses, equity_grants)

    Use paths like: SELECT * FROM 'data/lake/hris/employees.parquet'
    Or use the pre-registered views if available.

    Args:
        sql: A valid DuckDB SQL query.

    Returns:
        JSON string with query results or error message.
    """
    try:
        con = duckdb.connect()

        # Register common table aliases for convenience
        tables = {
            "employees": "hris/employees",
            "departments": "hris/departments",
            "positions": "hris/positions",
            "locations": "hris/locations",
            "employment_history": "hris/employment_history",
            "requisitions": "ats/requisitions",
            "candidates": "ats/candidates",
            "applications": "ats/applications",
            "interviews": "ats/interviews",
            "offers": "ats/offers",
            "performance_cycles": "performance/performance_cycles",
            "goals": "performance/goals",
            "performance_reviews": "performance/performance_reviews",
            "competency_assessments": "performance/competency_assessments",
            "salary_bands": "compensation/salary_bands",
            "base_salary": "compensation/base_salary",
            "bonuses": "compensation/bonuses",
            "equity_grants": "compensation/equity_grants",
        }

        for alias, path in tables.items():
            parquet_path = LAKE_DATA_DIR / f"{path}.parquet"
            if parquet_path.exists():
                con.execute(f"CREATE VIEW {alias} AS SELECT * FROM '{parquet_path}'")

        df = con.execute(sql).fetchdf()
        con.close()

        rows = []
        for _, record in df.iterrows():
            row = {col: _clean_value(record[col]) for col in df.columns}
            rows.append(row)

        # Limit to 200 rows to avoid huge responses
        truncated = len(rows) > 200
        rows = rows[:200]

        result = {"rows": rows, "count": len(rows)}
        if truncated:
            result["note"] = "Results truncated to 200 rows. Add LIMIT to your query for smaller results."

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})

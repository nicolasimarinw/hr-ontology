"""Converts raw CSVs to typed Parquet files organized by source system."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from rich.console import Console
from rich.table import Table

from config.settings import RAW_DATA_DIR, LAKE_DATA_DIR

console = Console()

# Schema definitions: column name -> pandas dtype
# date columns listed separately for pd.to_datetime conversion
SCHEMAS = {
    "hris": {
        "employees": {
            "dtypes": {
                "employee_id": "string",
                "first_name": "string",
                "last_name": "string",
                "email": "string",
                "gender": "category",
                "ethnicity": "category",
                "location_id": "category",
                "department_id": "string",
                "position_id": "string",
                "manager_id": "string",
                "job_level": "category",
                "job_family": "category",
                "status": "category",
                "termination_reason": "string",
            },
            "dates": ["hire_date", "birth_date", "termination_date"],
        },
        "departments": {
            "dtypes": {
                "dept_id": "string",
                "name": "string",
                "division_id": "category",
                "division_name": "category",
                "head_id": "string",
            },
            "dates": [],
        },
        "positions": {
            "dtypes": {
                "position_id": "string",
                "title": "string",
                "job_family": "category",
                "job_level": "category",
                "department_id": "string",
            },
            "dates": [],
        },
        "locations": {
            "dtypes": {
                "id": "string",
                "name": "string",
                "city": "string",
                "country": "category",
                "is_hq": "bool",
            },
            "dates": [],
        },
        "employment_history": {
            "dtypes": {
                "employee_id": "string",
                "event_type": "category",
                "from_position": "string",
                "to_position": "string",
                "from_department": "string",
                "to_department": "string",
            },
            "dates": ["effective_date"],
        },
    },
    "compensation": {
        "salary_bands": {
            "dtypes": {
                "band_id": "string",
                "job_family": "category",
                "job_family_name": "category",
                "job_level": "category",
                "job_level_name": "string",
                "min_salary": "int64",
                "midpoint": "int64",
                "max_salary": "int64",
                "currency": "category",
            },
            "dates": [],
        },
        "base_salary": {
            "dtypes": {
                "salary_id": "string",
                "employee_id": "string",
                "amount": "int64",
                "currency": "category",
                "reason": "category",
            },
            "dates": ["effective_date"],
        },
        "bonuses": {
            "dtypes": {
                "bonus_id": "string",
                "employee_id": "string",
                "type": "category",
                "target_pct": "float64",
                "actual_pct": "float64",
                "amount": "int64",
            },
            "dates": ["payout_date"],
        },
        "equity_grants": {
            "dtypes": {
                "grant_id": "string",
                "employee_id": "string",
                "shares": "int64",
                "vesting_schedule": "string",
                "exercise_price": "float64",
            },
            "dates": ["grant_date"],
        },
    },
    "ats": {
        "requisitions": {
            "dtypes": {
                "req_id": "string",
                "title": "string",
                "department_id": "string",
                "hiring_manager_id": "string",
                "status": "category",
                "headcount": "int64",
            },
            "dates": ["open_date", "close_date"],
        },
        "candidates": {
            "dtypes": {
                "candidate_id": "string",
                "name": "string",
                "email": "string",
                "source": "category",
            },
            "dates": [],
        },
        "applications": {
            "dtypes": {
                "application_id": "string",
                "candidate_id": "string",
                "req_id": "string",
                "status": "category",
                "stage": "category",
            },
            "dates": ["apply_date"],
        },
        "interviews": {
            "dtypes": {
                "interview_id": "string",
                "application_id": "string",
                "interviewer_id": "string",
                "type": "category",
                "score": "float64",
                "feedback": "string",
            },
            "dates": ["date"],
        },
        "offers": {
            "dtypes": {
                "offer_id": "string",
                "application_id": "string",
                "salary_offered": "int64",
                "equity_offered": "int64",
                "status": "category",
            },
            "dates": ["offer_date", "response_date", "start_date"],
        },
    },
    "performance": {
        "performance_cycles": {
            "dtypes": {
                "cycle_id": "string",
                "name": "string",
                "type": "category",
            },
            "dates": ["start_date", "end_date"],
        },
        "goals": {
            "dtypes": {
                "goal_id": "string",
                "employee_id": "string",
                "cycle_id": "string",
                "title": "string",
                "description": "string",
                "status": "category",
                "weight": "float64",
                "achievement_pct": "float64",
            },
            "dates": [],
        },
        "performance_reviews": {
            "dtypes": {
                "review_id": "string",
                "employee_id": "string",
                "reviewer_id": "string",
                "cycle_id": "string",
                "rating": "float64",
                "comments": "string",
                "strengths": "string",
                "development_areas": "string",
            },
            "dates": [],
        },
        "competency_assessments": {
            "dtypes": {
                "assessment_id": "string",
                "employee_id": "string",
                "cycle_id": "string",
                "skill_id": "string",
                "skill_name": "string",
                "current_level": "int64",
                "target_level": "int64",
            },
            "dates": [],
        },
    },
}


def build_lake() -> dict[str, int]:
    """Convert all raw CSVs to Parquet. Returns dict of table_name -> row_count."""
    console.print("\n[bold blue]Phase 2: Building Data Lake (CSV -> Parquet)[/bold blue]\n")

    results = {}

    for system_name, tables in SCHEMAS.items():
        system_out_dir = LAKE_DATA_DIR / system_name
        system_out_dir.mkdir(parents=True, exist_ok=True)

        for table_name, schema in tables.items():
            csv_path = RAW_DATA_DIR / system_name / f"{table_name}.csv"
            if not csv_path.exists():
                console.print(f"  [yellow]SKIP: {csv_path} not found[/yellow]")
                continue

            df = pd.read_csv(csv_path)

            # Apply dtypes
            for col, dtype in schema["dtypes"].items():
                if col in df.columns:
                    if dtype == "bool":
                        df[col] = df[col].astype(bool)
                    elif dtype == "category":
                        df[col] = df[col].astype("category")
                    elif dtype in ("int64", "float64"):
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    else:
                        df[col] = df[col].astype(str).replace("nan", pd.NA)

            # Convert date columns
            for col in schema["dates"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

            # Write Parquet
            parquet_path = system_out_dir / f"{table_name}.parquet"
            df.to_parquet(parquet_path, index=False, engine="pyarrow")

            results[f"{system_name}/{table_name}"] = len(df)

    # Print summary
    table = Table(title="Data Lake Contents")
    table.add_column("Table", style="cyan")
    table.add_column("Rows", justify="right", style="green")
    table.add_column("Path", style="dim")

    for name, count in sorted(results.items()):
        table.add_row(name, str(count), f"data/lake/{name}.parquet")

    console.print(table)
    console.print(f"\n[green]Total: {len(results)} Parquet files written to data/lake/[/green]")

    return results


if __name__ == "__main__":
    build_lake()

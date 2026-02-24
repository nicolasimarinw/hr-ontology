"""Test cross-system DuckDB views."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb
from config.settings import LAKE_DATA_DIR

con = duckdb.connect()
lake = str(LAKE_DATA_DIR).replace("\\", "/")

# Read SQL and substitute paths
sql_text = open("phase2_data_lake/queries/cross_system_views.sql").read()
sql_text = sql_text.replace("{lake}", lake)

# Split on the view boundary marker to get individual CREATE VIEW statements
# Each statement ends with a semicolon at the end of its block
statements = []
current = []
for line in sql_text.split("\n"):
    stripped = line.strip()
    if stripped.startswith("--"):
        continue
    current.append(line)
    if stripped.endswith(";"):
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)
        current = []

print(f"Found {len(statements)} SQL statements\n")

for i, stmt in enumerate(statements):
    first_line = stmt.split("\n")[0][:80]
    try:
        con.execute(stmt)
        print(f"OK [{i+1}]: {first_line}")
    except Exception as e:
        print(f"ERROR [{i+1}]: {first_line}")
        print(f"  -> {e}\n")

# Test View 1: Employee Full Profile
print("\n=== VIEW 1: Employee Full Profile ===")
result = con.execute("SELECT COUNT(*) FROM employee_full_profile").fetchone()
print(f"Rows: {result[0]}")
sample = con.execute("""
    SELECT employee_id, department_name, position_title, current_salary, latest_rating,
           ROUND(tenure_years, 1) as tenure_years
    FROM employee_full_profile LIMIT 5
""").fetchdf()
print(sample.to_string(index=False))

# Test View 2: Recruiting Funnel
print("\n=== VIEW 2: Recruiting Funnel ===")
result = con.execute("SELECT COUNT(*) FROM recruiting_funnel").fetchone()
print(f"Rows: {result[0]}")
source_perf = con.execute("""
    SELECT source, COUNT(*) as hires, ROUND(AVG(post_hire_avg_rating), 2) as avg_rating
    FROM recruiting_funnel
    WHERE post_hire_avg_rating IS NOT NULL
    GROUP BY source ORDER BY avg_rating DESC
""").fetchdf()
print(source_perf.to_string(index=False))

# Test View 3: Compensation Equity
print("\n=== VIEW 3: Compensation Equity ===")
result = con.execute("SELECT COUNT(*) FROM compensation_equity").fetchone()
print(f"Rows: {result[0]}")
equity = con.execute("""
    SELECT gender, ROUND(AVG(compa_ratio), 1) as avg_compa_ratio, COUNT(*) as n
    FROM compensation_equity WHERE compa_ratio IS NOT NULL
    GROUP BY gender ORDER BY avg_compa_ratio DESC
""").fetchdf()
print(equity.to_string(index=False))

# Test View 4: Flight Risk
print("\n=== VIEW 4: Flight Risk Features ===")
result = con.execute("SELECT COUNT(*) FROM flight_risk_features").fetchone()
print(f"Rows: {result[0]}")
risk = con.execute("""
    SELECT full_name, department_id, job_level, flight_risk_score
    FROM flight_risk_features
    WHERE flight_risk_score IS NOT NULL
    ORDER BY flight_risk_score DESC LIMIT 10
""").fetchdf()
print(risk.to_string(index=False))

con.close()
print("\nAll 4 views working correctly.")

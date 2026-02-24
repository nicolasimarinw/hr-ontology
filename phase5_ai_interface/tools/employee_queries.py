"""Cypher queries for the Employee Explorer page."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from phase5_ai_interface.tools.cypher_tools import query_graph


def get_employee_list() -> list[dict]:
    """Return all employees for the dropdown selector."""
    result = json.loads(query_graph("""
        MATCH (e:Employee)
        OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Department)
        RETURN e.employee_id AS id,
               e.first_name + ' ' + e.last_name AS name,
               d.name AS department,
               e.status AS status
        ORDER BY e.last_name, e.first_name
    """))
    return result.get("rows", [])


def get_employee_summary(emp_id: str) -> dict:
    """Return core properties + position + department + manager for an employee."""
    result = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})
        OPTIONAL MATCH (e)-[:HOLDS_POSITION]->(p:Position)
        OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Department)
        OPTIONAL MATCH (d)-[:PART_OF]->(div:Division)
        OPTIONAL MATCH (e)-[:LOCATED_AT]->(loc:Location)
        OPTIONAL MATCH (e)-[:REPORTS_TO]->(mgr:Employee)
        RETURN e.employee_id AS id,
               e.first_name + ' ' + e.last_name AS name,
               e.first_name AS first_name,
               e.last_name AS last_name,
               e.email AS email,
               e.hire_date AS hire_date,
               e.status AS status,
               e.gender AS gender,
               e.ethnicity AS ethnicity,
               e.job_level AS job_level,
               e.department_id AS department_id,
               p.title AS position,
               d.name AS department,
               div.name AS division,
               loc.city + ', ' + loc.state AS location,
               mgr.employee_id AS manager_id,
               mgr.first_name + ' ' + mgr.last_name AS manager_name
    """, params={"eid": emp_id}))
    rows = result.get("rows", [])
    return rows[0] if rows else {}


def get_manager_chain(emp_id: str) -> list[dict]:
    """Return upward reporting chain from employee to CEO."""
    result = json.loads(query_graph("""
        MATCH path = (e:Employee {employee_id: $eid})-[:REPORTS_TO*1..10]->(mgr:Employee)
        WITH nodes(path) AS chain
        UNWIND range(1, size(chain)-1) AS i
        WITH chain[i] AS m, i AS depth
        RETURN m.employee_id AS id,
               m.first_name + ' ' + m.last_name AS name,
               m.job_level AS job_level,
               depth
        ORDER BY depth
    """, params={"eid": emp_id}))
    return result.get("rows", [])


def get_direct_reports(emp_id: str) -> list[dict]:
    """Return direct reports for an employee."""
    result = json.loads(query_graph("""
        MATCH (report:Employee)-[:REPORTS_TO]->(e:Employee {employee_id: $eid})
        OPTIONAL MATCH (report)-[:HOLDS_POSITION]->(p:Position)
        RETURN report.employee_id AS id,
               report.first_name + ' ' + report.last_name AS name,
               report.job_level AS job_level,
               report.status AS status,
               p.title AS position
        ORDER BY report.last_name
    """, params={"eid": emp_id}))
    return result.get("rows", [])


def get_skills(emp_id: str) -> list[dict]:
    """Return skills with proficiency for an employee."""
    result = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[h:HAS_SKILL]->(s:Skill)
        RETURN s.skill_id AS id,
               s.name AS name,
               s.category AS category,
               h.proficiency_level AS proficiency,
               h.assessed_date AS assessed_date
        ORDER BY s.category, s.name
    """, params={"eid": emp_id}))
    return result.get("rows", [])


def get_performance_reviews(emp_id: str) -> list[dict]:
    """Return performance reviews with cycle and reviewer."""
    result = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[:REVIEWED_IN]->(pr:PerformanceReview)
        OPTIONAL MATCH (pr)-[:PART_OF_CYCLE]->(pc:PerformanceCycle)
        OPTIONAL MATCH (pr)-[:REVIEWED_BY]->(reviewer:Employee)
        RETURN pr.review_id AS id,
               pr.rating AS rating,
               pr.review_date AS review_date,
               pr.comments AS comments,
               pc.name AS cycle_name,
               pc.cycle_id AS cycle_id,
               reviewer.first_name + ' ' + reviewer.last_name AS reviewer_name,
               reviewer.employee_id AS reviewer_id
        ORDER BY pr.review_date DESC
    """, params={"eid": emp_id}))
    return result.get("rows", [])


def get_goals(emp_id: str) -> list[dict]:
    """Return goals with status and achievement."""
    result = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[:SET_GOAL]->(g:Goal)
        OPTIONAL MATCH (g)-[:GOAL_IN_CYCLE]->(pc:PerformanceCycle)
        RETURN g.goal_id AS id,
               g.description AS description,
               g.status AS status,
               g.category AS category,
               g.achievement_pct AS achievement_pct,
               pc.name AS cycle_name
        ORDER BY pc.name DESC, g.status
    """, params={"eid": emp_id}))
    return result.get("rows", [])


def get_compensation(emp_id: str) -> dict:
    """Return salary history, bonuses, equity grants, and salary band context."""
    salaries = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[:EARNS_BASE]->(s:BaseSalary)
        RETURN s.salary_id AS id,
               s.amount AS amount,
               s.currency AS currency,
               s.effective_date AS effective_date,
               s.pay_frequency AS pay_frequency
        ORDER BY s.effective_date DESC
    """, params={"eid": emp_id}))

    bonuses = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[:RECEIVED_BONUS]->(b:Bonus)
        RETURN b.bonus_id AS id,
               b.amount AS amount,
               b.bonus_type AS type,
               b.payment_date AS payment_date
        ORDER BY b.payment_date DESC
    """, params={"eid": emp_id}))

    equity = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[:GRANTED_EQUITY]->(eq:EquityGrant)
        RETURN eq.grant_id AS id,
               eq.shares AS shares,
               eq.grant_date AS grant_date,
               eq.vesting_schedule AS vesting_schedule,
               eq.strike_price AS strike_price
        ORDER BY eq.grant_date DESC
    """, params={"eid": emp_id}))

    band = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[:HOLDS_POSITION]->(p:Position)-[:IN_SALARY_BAND]->(b:SalaryBand)
        RETURN b.band_id AS id,
               b.job_family AS job_family,
               b.job_level AS job_level,
               b.min_salary AS min_salary,
               b.midpoint AS midpoint,
               b.max_salary AS max_salary
    """, params={"eid": emp_id}))

    return {
        "salaries": salaries.get("rows", []),
        "bonuses": bonuses.get("rows", []),
        "equity": equity.get("rows", []),
        "salary_band": band.get("rows", [{}])[0] if band.get("rows") else {},
    }


def get_temporal_events(emp_id: str) -> list[dict]:
    """Return lifecycle events for an employee."""
    result = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[:EXPERIENCED_EVENT]->(te:TemporalEvent)
        RETURN te.event_id AS id,
               te.event_type AS event_type,
               te.event_date AS event_date,
               te.description AS description
        ORDER BY te.event_date DESC
    """, params={"eid": emp_id}))
    return result.get("rows", [])


def get_relationship_counts(emp_id: str) -> list[dict]:
    """Return count of relationships by type for an employee."""
    result = json.loads(query_graph("""
        MATCH (e:Employee {employee_id: $eid})-[r]-()
        RETURN type(r) AS relationship, count(r) AS count
        ORDER BY count DESC
    """, params={"eid": emp_id}))
    return result.get("rows", [])

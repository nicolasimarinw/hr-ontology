"""Property graph schema: Pydantic models for all Neo4j node and edge types."""

from typing import Optional
from pydantic import BaseModel


# =============================================================================
# Node Models
# =============================================================================

class NodeSchema(BaseModel):
    """Base schema for all graph nodes."""
    labels: list[str]
    id_property: str
    required: list[str]
    optional: list[str] = []
    indexes: list[str] = []


class EdgeSchema(BaseModel):
    """Base schema for all graph relationships."""
    type: str
    source_label: str
    target_label: str
    properties: list[str] = []


# --- Agent nodes ---

EMPLOYEE = NodeSchema(
    labels=["Person", "Employee"],
    id_property="employee_id",
    required=["employee_id", "first_name", "last_name", "email", "hire_date",
              "gender", "ethnicity", "job_level", "job_family", "status"],
    optional=["birth_date", "termination_date", "termination_reason"],
    indexes=["employee_id", "email"],
)

CANDIDATE = NodeSchema(
    labels=["Person", "Candidate"],
    id_property="candidate_id",
    required=["candidate_id", "name", "email"],
    optional=["source"],
    indexes=["candidate_id"],
)

# --- Organizational Unit nodes ---

DIVISION = NodeSchema(
    labels=["OrganizationalUnit", "Division"],
    id_property="division_id",
    required=["division_id", "name"],
    indexes=["division_id"],
)

DEPARTMENT = NodeSchema(
    labels=["OrganizationalUnit", "Department"],
    id_property="dept_id",
    required=["dept_id", "name", "division_id"],
    optional=["division_name"],
    indexes=["dept_id"],
)

LOCATION = NodeSchema(
    labels=["OrganizationalUnit", "Location"],
    id_property="location_id",
    required=["location_id", "name", "city", "country"],
    optional=["is_hq"],
    indexes=["location_id"],
)

# --- Role nodes ---

POSITION = NodeSchema(
    labels=["Role", "Position"],
    id_property="position_id",
    required=["position_id", "title", "job_family", "job_level", "department_id"],
    indexes=["position_id"],
)

JOB_FAMILY = NodeSchema(
    labels=["Role", "JobFamily"],
    id_property="family_id",
    required=["family_id", "name"],
    indexes=["family_id"],
)

JOB_LEVEL = NodeSchema(
    labels=["Role", "JobLevel"],
    id_property="level_id",
    required=["level_id", "name", "rank"],
    indexes=["level_id"],
)

# --- Competency nodes ---

SKILL = NodeSchema(
    labels=["Competency", "Skill"],
    id_property="skill_id",
    required=["skill_id", "name", "category"],
    indexes=["skill_id"],
)

# --- Talent Process nodes ---

REQUISITION = NodeSchema(
    labels=["TalentProcess", "Requisition"],
    id_property="req_id",
    required=["req_id", "title", "status"],
    optional=["open_date", "close_date", "headcount"],
    indexes=["req_id"],
)

APPLICATION = NodeSchema(
    labels=["TalentProcess", "Application"],
    id_property="application_id",
    required=["application_id", "apply_date", "status", "stage"],
    indexes=["application_id"],
)

INTERVIEW = NodeSchema(
    labels=["TalentProcess", "Interview"],
    id_property="interview_id",
    required=["interview_id", "date", "type", "score"],
    optional=["feedback"],
    indexes=["interview_id"],
)

OFFER = NodeSchema(
    labels=["TalentProcess", "Offer"],
    id_property="offer_id",
    required=["offer_id", "salary_offered", "status"],
    optional=["equity_offered", "offer_date", "response_date", "start_date"],
    indexes=["offer_id"],
)

PERFORMANCE_REVIEW = NodeSchema(
    labels=["TalentProcess", "PerformanceReview"],
    id_property="review_id",
    required=["review_id", "rating"],
    optional=["comments", "strengths", "development_areas"],
    indexes=["review_id"],
)

GOAL = NodeSchema(
    labels=["TalentProcess", "Goal"],
    id_property="goal_id",
    required=["goal_id", "title", "status", "weight", "achievement_pct"],
    optional=["description"],
    indexes=["goal_id"],
)

# --- Compensation nodes ---

SALARY_BAND = NodeSchema(
    labels=["CompensationElement", "SalaryBand"],
    id_property="band_id",
    required=["band_id", "job_family", "job_level", "min_salary", "midpoint", "max_salary"],
    optional=["currency"],
    indexes=["band_id"],
)

BASE_SALARY = NodeSchema(
    labels=["CompensationElement", "BaseSalary"],
    id_property="salary_id",
    required=["salary_id", "amount", "effective_date", "reason"],
    optional=["currency"],
    indexes=["salary_id"],
)

BONUS = NodeSchema(
    labels=["CompensationElement", "Bonus"],
    id_property="bonus_id",
    required=["bonus_id", "type", "amount", "payout_date"],
    optional=["target_pct", "actual_pct"],
    indexes=["bonus_id"],
)

EQUITY_GRANT = NodeSchema(
    labels=["CompensationElement", "EquityGrant"],
    id_property="grant_id",
    required=["grant_id", "grant_date", "shares"],
    optional=["vesting_schedule", "exercise_price"],
    indexes=["grant_id"],
)

# --- Performance Cycle ---

PERFORMANCE_CYCLE = NodeSchema(
    labels=["PerformanceCycle"],
    id_property="cycle_id",
    required=["cycle_id", "name", "start_date", "end_date", "type"],
    indexes=["cycle_id"],
)

# --- Source Channel ---

SOURCE_CHANNEL = NodeSchema(
    labels=["SourceChannel"],
    id_property="channel_name",
    required=["channel_name"],
    indexes=["channel_name"],
)

# --- Temporal Events ---

TEMPORAL_EVENT = NodeSchema(
    labels=["TemporalEvent"],
    id_property="event_id",
    required=["event_id", "event_type", "effective_date"],
    optional=["from_position", "to_position", "from_department", "to_department"],
    indexes=["event_id"],
)


# =============================================================================
# All node schemas (for iteration)
# =============================================================================

ALL_NODE_SCHEMAS = {
    "Employee": EMPLOYEE,
    "Candidate": CANDIDATE,
    "Division": DIVISION,
    "Department": DEPARTMENT,
    "Location": LOCATION,
    "Position": POSITION,
    "JobFamily": JOB_FAMILY,
    "JobLevel": JOB_LEVEL,
    "Skill": SKILL,
    "Requisition": REQUISITION,
    "Application": APPLICATION,
    "Interview": INTERVIEW,
    "Offer": OFFER,
    "PerformanceReview": PERFORMANCE_REVIEW,
    "Goal": GOAL,
    "SalaryBand": SALARY_BAND,
    "BaseSalary": BASE_SALARY,
    "Bonus": BONUS,
    "EquityGrant": EQUITY_GRANT,
    "PerformanceCycle": PERFORMANCE_CYCLE,
    "SourceChannel": SOURCE_CHANNEL,
    "TemporalEvent": TEMPORAL_EVENT,
}

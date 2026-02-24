"""Relationship type definitions for the HR property graph."""

from phase3_ontology.schema import EdgeSchema

# =============================================================================
# Organizational Structure
# =============================================================================

REPORTS_TO = EdgeSchema(
    type="REPORTS_TO",
    source_label="Employee",
    target_label="Employee",
    properties=["effective_date"],
)

BELONGS_TO = EdgeSchema(
    type="BELONGS_TO",
    source_label="Employee",
    target_label="Department",
    properties=["effective_date"],
)

PART_OF = EdgeSchema(
    type="PART_OF",
    source_label="Department",
    target_label="Division",
)

LOCATED_AT = EdgeSchema(
    type="LOCATED_AT",
    source_label="Employee",
    target_label="Location",
)

HOLDS_POSITION = EdgeSchema(
    type="HOLDS_POSITION",
    source_label="Employee",
    target_label="Position",
    properties=["start_date", "end_date"],
)

POSITION_IN = EdgeSchema(
    type="POSITION_IN",
    source_label="Position",
    target_label="Department",
)

IN_JOB_FAMILY = EdgeSchema(
    type="IN_JOB_FAMILY",
    source_label="Position",
    target_label="JobFamily",
)

AT_LEVEL = EdgeSchema(
    type="AT_LEVEL",
    source_label="Position",
    target_label="JobLevel",
)

# =============================================================================
# Skills
# =============================================================================

HAS_SKILL = EdgeSchema(
    type="HAS_SKILL",
    source_label="Employee",
    target_label="Skill",
    properties=["proficiency_level", "assessed_date"],
)

REQUIRES_SKILL = EdgeSchema(
    type="REQUIRES_SKILL",
    source_label="Position",
    target_label="Skill",
)

DEMONSTRATES_COMPETENCY = EdgeSchema(
    type="DEMONSTRATES_COMPETENCY",
    source_label="PerformanceReview",
    target_label="Skill",
    properties=["current_level", "target_level"],
)

# =============================================================================
# Talent Acquisition
# =============================================================================

APPLIED_FOR = EdgeSchema(
    type="APPLIED_FOR",
    source_label="Candidate",
    target_label="Requisition",
    properties=["application_date", "status", "stage"],
)

HAS_APPLICATION = EdgeSchema(
    type="HAS_APPLICATION",
    source_label="Candidate",
    target_label="Application",
)

APPLICATION_FOR = EdgeSchema(
    type="APPLICATION_FOR",
    source_label="Application",
    target_label="Requisition",
)

HAS_INTERVIEW = EdgeSchema(
    type="HAS_INTERVIEW",
    source_label="Application",
    target_label="Interview",
)

INTERVIEWED_BY = EdgeSchema(
    type="INTERVIEWED_BY",
    source_label="Interview",
    target_label="Employee",
)

HAS_OFFER = EdgeSchema(
    type="HAS_OFFER",
    source_label="Application",
    target_label="Offer",
)

FILLS_REQUISITION = EdgeSchema(
    type="FILLS_REQUISITION",
    source_label="Employee",
    target_label="Requisition",
    properties=["hire_date"],
)

SOURCED_FROM = EdgeSchema(
    type="SOURCED_FROM",
    source_label="Candidate",
    target_label="SourceChannel",
)

REQUISITION_FOR = EdgeSchema(
    type="REQUISITION_FOR",
    source_label="Requisition",
    target_label="Department",
)

# =============================================================================
# Performance
# =============================================================================

REVIEWED_IN = EdgeSchema(
    type="REVIEWED_IN",
    source_label="Employee",
    target_label="PerformanceReview",
)

REVIEWED_BY = EdgeSchema(
    type="REVIEWED_BY",
    source_label="PerformanceReview",
    target_label="Employee",
    properties=["role"],
)

SET_GOAL = EdgeSchema(
    type="SET_GOAL",
    source_label="Employee",
    target_label="Goal",
)

PART_OF_CYCLE = EdgeSchema(
    type="PART_OF_CYCLE",
    source_label="PerformanceReview",
    target_label="PerformanceCycle",
)

GOAL_IN_CYCLE = EdgeSchema(
    type="GOAL_IN_CYCLE",
    source_label="Goal",
    target_label="PerformanceCycle",
)

# =============================================================================
# Compensation
# =============================================================================

EARNS_BASE = EdgeSchema(
    type="EARNS_BASE",
    source_label="Employee",
    target_label="BaseSalary",
)

RECEIVED_BONUS = EdgeSchema(
    type="RECEIVED_BONUS",
    source_label="Employee",
    target_label="Bonus",
)

GRANTED_EQUITY = EdgeSchema(
    type="GRANTED_EQUITY",
    source_label="Employee",
    target_label="EquityGrant",
)

IN_SALARY_BAND = EdgeSchema(
    type="IN_SALARY_BAND",
    source_label="Position",
    target_label="SalaryBand",
)

# =============================================================================
# Lifecycle Events
# =============================================================================

EXPERIENCED_EVENT = EdgeSchema(
    type="EXPERIENCED_EVENT",
    source_label="Employee",
    target_label="TemporalEvent",
)


# =============================================================================
# All edge schemas (for iteration)
# =============================================================================

ALL_EDGE_SCHEMAS = {
    "REPORTS_TO": REPORTS_TO,
    "BELONGS_TO": BELONGS_TO,
    "PART_OF": PART_OF,
    "LOCATED_AT": LOCATED_AT,
    "HOLDS_POSITION": HOLDS_POSITION,
    "POSITION_IN": POSITION_IN,
    "IN_JOB_FAMILY": IN_JOB_FAMILY,
    "AT_LEVEL": AT_LEVEL,
    "HAS_SKILL": HAS_SKILL,
    "REQUIRES_SKILL": REQUIRES_SKILL,
    "DEMONSTRATES_COMPETENCY": DEMONSTRATES_COMPETENCY,
    "APPLIED_FOR": APPLIED_FOR,
    "HAS_APPLICATION": HAS_APPLICATION,
    "APPLICATION_FOR": APPLICATION_FOR,
    "HAS_INTERVIEW": HAS_INTERVIEW,
    "INTERVIEWED_BY": INTERVIEWED_BY,
    "HAS_OFFER": HAS_OFFER,
    "FILLS_REQUISITION": FILLS_REQUISITION,
    "SOURCED_FROM": SOURCED_FROM,
    "REQUISITION_FOR": REQUISITION_FOR,
    "REVIEWED_IN": REVIEWED_IN,
    "REVIEWED_BY": REVIEWED_BY,
    "SET_GOAL": SET_GOAL,
    "PART_OF_CYCLE": PART_OF_CYCLE,
    "GOAL_IN_CYCLE": GOAL_IN_CYCLE,
    "EARNS_BASE": EARNS_BASE,
    "RECEIVED_BONUS": RECEIVED_BONUS,
    "GRANTED_EQUITY": GRANTED_EQUITY,
    "IN_SALARY_BAND": IN_SALARY_BAND,
    "EXPERIENCED_EVENT": EXPERIENCED_EVENT,
}

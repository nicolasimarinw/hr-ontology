"""Data lake -> graph mapping configuration.

Defines how Parquet tables map to Neo4j nodes and how cross-table joins
produce Neo4j relationships.
"""

# =============================================================================
# Node Mappings: Parquet table -> Neo4j node
# =============================================================================

NODE_MAPPINGS = [
    # --- Organizational Units ---
    {
        "source": "hris/departments",
        "label": "Department",
        "id_field": "dept_id",
        "properties": {
            "dept_id": "dept_id",
            "name": "name",
            "division_id": "division_id",
            "division_name": "division_name",
        },
    },
    {
        "source": "hris/locations",
        "label": "Location",
        "id_field": "id",
        "properties": {
            "location_id": "id",
            "name": "name",
            "city": "city",
            "country": "country",
            "is_hq": "is_hq",
        },
    },
    # Divisions are derived from departments (unique division_id values)
    {
        "source": "hris/departments",
        "label": "Division",
        "id_field": "division_id",
        "deduplicate_on": "division_id",
        "properties": {
            "division_id": "division_id",
            "name": "division_name",
        },
    },
    # --- Employees ---
    {
        "source": "hris/employees",
        "label": "Employee",
        "id_field": "employee_id",
        "properties": {
            "employee_id": "employee_id",
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "email",
            "hire_date": "hire_date",
            "birth_date": "birth_date",
            "gender": "gender",
            "ethnicity": "ethnicity",
            "location_id": "location_id",
            "department_id": "department_id",
            "position_id": "position_id",
            "manager_id": "manager_id",
            "job_level": "job_level",
            "job_family": "job_family",
            "status": "status",
            "termination_date": "termination_date",
            "termination_reason": "termination_reason",
        },
    },
    # --- Positions ---
    {
        "source": "hris/positions",
        "label": "Position",
        "id_field": "position_id",
        "properties": {
            "position_id": "position_id",
            "title": "title",
            "job_family": "job_family",
            "job_level": "job_level",
            "department_id": "department_id",
        },
    },
    # Job Families (derived from positions, deduplicated)
    {
        "source": "hris/positions",
        "label": "JobFamily",
        "id_field": "job_family",
        "deduplicate_on": "job_family",
        "properties": {
            "family_id": "job_family",
            "name": "job_family",
        },
    },
    # Job Levels (derived from positions, deduplicated)
    {
        "source": "hris/positions",
        "label": "JobLevel",
        "id_field": "job_level",
        "deduplicate_on": "job_level",
        "properties": {
            "level_id": "job_level",
            "name": "job_level",
        },
    },
    # --- Skills ---
    # Skills are loaded from the company profile, not from a Parquet file
    {
        "source": "__skill_catalog__",
        "label": "Skill",
        "id_field": "skill_id",
        "properties": {
            "skill_id": "id",
            "name": "name",
            "category": "category",
        },
    },
    # --- ATS ---
    {
        "source": "ats/requisitions",
        "label": "Requisition",
        "id_field": "req_id",
        "properties": {
            "req_id": "req_id",
            "title": "title",
            "department_id": "department_id",
            "status": "status",
            "open_date": "open_date",
            "close_date": "close_date",
            "headcount": "headcount",
        },
    },
    {
        "source": "ats/candidates",
        "label": "Candidate",
        "id_field": "candidate_id",
        "properties": {
            "candidate_id": "candidate_id",
            "name": "name",
            "email": "email",
            "source": "source",
        },
    },
    {
        "source": "ats/applications",
        "label": "Application",
        "id_field": "application_id",
        "properties": {
            "application_id": "application_id",
            "apply_date": "apply_date",
            "status": "status",
            "stage": "stage",
        },
    },
    {
        "source": "ats/interviews",
        "label": "Interview",
        "id_field": "interview_id",
        "properties": {
            "interview_id": "interview_id",
            "date": "date",
            "type": "type",
            "score": "score",
            "feedback": "feedback",
        },
    },
    {
        "source": "ats/offers",
        "label": "Offer",
        "id_field": "offer_id",
        "properties": {
            "offer_id": "offer_id",
            "salary_offered": "salary_offered",
            "equity_offered": "equity_offered",
            "status": "status",
            "offer_date": "offer_date",
            "response_date": "response_date",
            "start_date": "start_date",
        },
    },
    # Source Channels (derived from candidates, deduplicated)
    {
        "source": "ats/candidates",
        "label": "SourceChannel",
        "id_field": "source",
        "deduplicate_on": "source",
        "properties": {
            "channel_name": "source",
        },
    },
    # --- Performance ---
    {
        "source": "performance/performance_cycles",
        "label": "PerformanceCycle",
        "id_field": "cycle_id",
        "properties": {
            "cycle_id": "cycle_id",
            "name": "name",
            "start_date": "start_date",
            "end_date": "end_date",
            "type": "type",
        },
    },
    {
        "source": "performance/performance_reviews",
        "label": "PerformanceReview",
        "id_field": "review_id",
        "properties": {
            "review_id": "review_id",
            "rating": "rating",
            "comments": "comments",
            "strengths": "strengths",
            "development_areas": "development_areas",
        },
    },
    {
        "source": "performance/goals",
        "label": "Goal",
        "id_field": "goal_id",
        "properties": {
            "goal_id": "goal_id",
            "title": "title",
            "description": "description",
            "status": "status",
            "weight": "weight",
            "achievement_pct": "achievement_pct",
        },
    },
    # --- Compensation ---
    {
        "source": "compensation/salary_bands",
        "label": "SalaryBand",
        "id_field": "band_id",
        "properties": {
            "band_id": "band_id",
            "job_family": "job_family",
            "job_level": "job_level",
            "min_salary": "min_salary",
            "midpoint": "midpoint",
            "max_salary": "max_salary",
            "currency": "currency",
        },
    },
    {
        "source": "compensation/base_salary",
        "label": "BaseSalary",
        "id_field": "salary_id",
        "properties": {
            "salary_id": "salary_id",
            "amount": "amount",
            "currency": "currency",
            "effective_date": "effective_date",
            "reason": "reason",
        },
    },
    {
        "source": "compensation/bonuses",
        "label": "Bonus",
        "id_field": "bonus_id",
        "properties": {
            "bonus_id": "bonus_id",
            "type": "type",
            "target_pct": "target_pct",
            "actual_pct": "actual_pct",
            "amount": "amount",
            "payout_date": "payout_date",
        },
    },
    {
        "source": "compensation/equity_grants",
        "label": "EquityGrant",
        "id_field": "grant_id",
        "properties": {
            "grant_id": "grant_id",
            "grant_date": "grant_date",
            "shares": "shares",
            "vesting_schedule": "vesting_schedule",
            "exercise_price": "exercise_price",
        },
    },
    # --- Employment History (as temporal events) ---
    {
        "source": "hris/employment_history",
        "label": "TemporalEvent",
        "id_field": "__row_index__",
        "auto_id_prefix": "EVT",
        "properties": {
            "event_type": "event_type",
            "effective_date": "effective_date",
            "from_position": "from_position",
            "to_position": "to_position",
            "from_department": "from_department",
            "to_department": "to_department",
        },
    },
]


# =============================================================================
# Edge Mappings: how to create relationships from the data
# =============================================================================

EDGE_MAPPINGS = [
    # --- Organizational ---
    {
        "type": "REPORTS_TO",
        "source_table": "hris/employees",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "manager_id",
        "target_label": "Employee",
        "filter": "manager_id IS NOT NULL AND CAST(manager_id AS VARCHAR) != 'nan'",
    },
    {
        "type": "BELONGS_TO",
        "source_table": "hris/employees",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "department_id",
        "target_label": "Department",
    },
    {
        "type": "PART_OF",
        "source_table": "hris/departments",
        "source_id": "dept_id",
        "source_label": "Department",
        "target_id": "division_id",
        "target_label": "Division",
    },
    {
        "type": "LOCATED_AT",
        "source_table": "hris/employees",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "location_id",
        "target_label": "Location",
    },
    {
        "type": "HOLDS_POSITION",
        "source_table": "hris/employees",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "position_id",
        "target_label": "Position",
    },
    {
        "type": "POSITION_IN",
        "source_table": "hris/positions",
        "source_id": "position_id",
        "source_label": "Position",
        "target_id": "department_id",
        "target_label": "Department",
    },
    {
        "type": "IN_JOB_FAMILY",
        "source_table": "hris/positions",
        "source_id": "position_id",
        "source_label": "Position",
        "target_id": "job_family",
        "target_label": "JobFamily",
    },
    {
        "type": "AT_LEVEL",
        "source_table": "hris/positions",
        "source_id": "position_id",
        "source_label": "Position",
        "target_id": "job_level",
        "target_label": "JobLevel",
    },
    # --- ATS ---
    {
        "type": "HAS_APPLICATION",
        "source_table": "ats/applications",
        "source_id": "candidate_id",
        "source_label": "Candidate",
        "target_id": "application_id",
        "target_label": "Application",
    },
    {
        "type": "APPLICATION_FOR",
        "source_table": "ats/applications",
        "source_id": "application_id",
        "source_label": "Application",
        "target_id": "req_id",
        "target_label": "Requisition",
    },
    {
        "type": "HAS_INTERVIEW",
        "source_table": "ats/interviews",
        "source_id": "application_id",
        "source_label": "Application",
        "target_id": "interview_id",
        "target_label": "Interview",
    },
    {
        "type": "INTERVIEWED_BY",
        "source_table": "ats/interviews",
        "source_id": "interview_id",
        "source_label": "Interview",
        "target_id": "interviewer_id",
        "target_label": "Employee",
        "filter": "interviewer_id IS NOT NULL AND CAST(interviewer_id AS VARCHAR) != 'nan'",
    },
    {
        "type": "HAS_OFFER",
        "source_table": "ats/offers",
        "source_id": "application_id",
        "source_label": "Application",
        "target_id": "offer_id",
        "target_label": "Offer",
    },
    {
        "type": "SOURCED_FROM",
        "source_table": "ats/candidates",
        "source_id": "candidate_id",
        "source_label": "Candidate",
        "target_id": "source",
        "target_label": "SourceChannel",
    },
    {
        "type": "REQUISITION_FOR",
        "source_table": "ats/requisitions",
        "source_id": "req_id",
        "source_label": "Requisition",
        "target_id": "department_id",
        "target_label": "Department",
    },
    # --- Performance ---
    {
        "type": "REVIEWED_IN",
        "source_table": "performance/performance_reviews",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "review_id",
        "target_label": "PerformanceReview",
    },
    {
        "type": "REVIEWED_BY",
        "source_table": "performance/performance_reviews",
        "source_id": "review_id",
        "source_label": "PerformanceReview",
        "target_id": "reviewer_id",
        "target_label": "Employee",
    },
    {
        "type": "PART_OF_CYCLE",
        "source_table": "performance/performance_reviews",
        "source_id": "review_id",
        "source_label": "PerformanceReview",
        "target_id": "cycle_id",
        "target_label": "PerformanceCycle",
    },
    {
        "type": "SET_GOAL",
        "source_table": "performance/goals",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "goal_id",
        "target_label": "Goal",
    },
    {
        "type": "GOAL_IN_CYCLE",
        "source_table": "performance/goals",
        "source_id": "goal_id",
        "source_label": "Goal",
        "target_id": "cycle_id",
        "target_label": "PerformanceCycle",
    },
    # --- Compensation ---
    {
        "type": "EARNS_BASE",
        "source_table": "compensation/base_salary",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "salary_id",
        "target_label": "BaseSalary",
    },
    {
        "type": "RECEIVED_BONUS",
        "source_table": "compensation/bonuses",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "bonus_id",
        "target_label": "Bonus",
    },
    {
        "type": "GRANTED_EQUITY",
        "source_table": "compensation/equity_grants",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "grant_id",
        "target_label": "EquityGrant",
    },
    {
        "type": "IN_SALARY_BAND",
        "source_table": "compensation/salary_bands",
        "source_id": "band_id",
        "source_label": "SalaryBand",
        "join": {
            "table": "hris/positions",
            "on_source": ["job_family", "job_level"],
            "on_target": ["job_family", "job_level"],
            "target_id": "position_id",
        },
        "target_label": "Position",
        "reverse": True,  # Position -> SalaryBand
    },
    # --- Competency Assessments -> Skills ---
    {
        "type": "HAS_SKILL",
        "source_table": "performance/competency_assessments",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "skill_id",
        "target_label": "Skill",
        "edge_properties": {
            "proficiency_level": "current_level",
            "target_level": "target_level",
        },
    },
    # --- Employment History -> Events ---
    {
        "type": "EXPERIENCED_EVENT",
        "source_table": "hris/employment_history",
        "source_id": "employee_id",
        "source_label": "Employee",
        "target_id": "__row_index__",
        "target_label": "TemporalEvent",
    },
]

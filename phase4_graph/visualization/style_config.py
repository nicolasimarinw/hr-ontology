"""Visual style configuration for graph visualizations."""

# Node colors by label
NODE_COLORS = {
    "Employee": "#4A90D9",       # Blue
    "Candidate": "#9B59B6",      # Purple
    "Department": "#E67E22",     # Orange
    "Division": "#D35400",       # Dark orange
    "Location": "#1ABC9C",       # Teal
    "Position": "#3498DB",       # Light blue
    "JobFamily": "#2980B9",      # Medium blue
    "JobLevel": "#2471A3",       # Dark blue
    "Skill": "#27AE60",          # Green
    "Requisition": "#F39C12",    # Yellow
    "Application": "#F1C40F",    # Gold
    "Interview": "#E74C3C",      # Red
    "Offer": "#2ECC71",          # Bright green
    "PerformanceReview": "#8E44AD",  # Purple
    "Goal": "#16A085",           # Dark teal
    "SalaryBand": "#D4AC0D",     # Dark gold
    "BaseSalary": "#28B463",     # Money green
    "Bonus": "#1E8449",          # Dark green
    "EquityGrant": "#117A65",    # Forest green
    "PerformanceCycle": "#7D3C98",   # Dark purple
    "SourceChannel": "#CA6F1E",  # Brown
    "TemporalEvent": "#95A5A6",  # Gray
}

# Node sizes by label (pixels)
NODE_SIZES = {
    "Employee": 20,
    "Candidate": 15,
    "Department": 30,
    "Division": 35,
    "Location": 25,
    "Position": 12,
    "JobFamily": 25,
    "JobLevel": 20,
    "Skill": 18,
    "Requisition": 15,
    "Application": 10,
    "Interview": 10,
    "Offer": 12,
    "PerformanceReview": 12,
    "Goal": 10,
    "SalaryBand": 15,
    "BaseSalary": 10,
    "Bonus": 10,
    "EquityGrant": 10,
    "PerformanceCycle": 20,
    "SourceChannel": 20,
    "TemporalEvent": 10,
}

# Edge colors by type
EDGE_COLORS = {
    # Organizational Structure
    "REPORTS_TO": "#34495E",
    "BELONGS_TO": "#E67E22",
    "PART_OF": "#D35400",
    "LOCATED_AT": "#1ABC9C",
    "HOLDS_POSITION": "#3498DB",
    "POSITION_IN": "#2980B9",
    "IN_JOB_FAMILY": "#2471A3",
    "AT_LEVEL": "#1F618D",
    # Skills
    "HAS_SKILL": "#27AE60",
    "REQUIRES_SKILL": "#229954",
    "DEMONSTRATES_COMPETENCY": "#1E8449",
    # Talent Acquisition
    "APPLIED_FOR": "#F39C12",
    "HAS_APPLICATION": "#F1C40F",
    "APPLICATION_FOR": "#D4AC0D",
    "HAS_INTERVIEW": "#E74C3C",
    "INTERVIEWED_BY": "#CB4335",
    "HAS_OFFER": "#2ECC71",
    "FILLS_REQUISITION": "#28B463",
    "SOURCED_FROM": "#CA6F1E",
    "REQUISITION_FOR": "#BA4A00",
    # Performance
    "REVIEWED_IN": "#8E44AD",
    "REVIEWED_BY": "#7D3C98",
    "SET_GOAL": "#16A085",
    "PART_OF_CYCLE": "#6C3483",
    "GOAL_IN_CYCLE": "#148F77",
    # Compensation
    "EARNS_BASE": "#28B463",
    "RECEIVED_BONUS": "#1E8449",
    "GRANTED_EQUITY": "#117A65",
    "IN_SALARY_BAND": "#D4AC0D",
    # Lifecycle
    "EXPERIENCED_EVENT": "#95A5A6",
    "DEFAULT": "#BDC3C7",
}

# Flight risk color scale (score -> color)
RISK_COLORS = {
    "low": "#27AE60",      # Green (0-25)
    "medium": "#F39C12",   # Yellow (25-50)
    "high": "#E67E22",     # Orange (50-75)
    "critical": "#E74C3C", # Red (75-100)
}


def risk_color(score: float) -> str:
    """Return color for a flight risk score."""
    if score >= 75:
        return RISK_COLORS["critical"]
    elif score >= 50:
        return RISK_COLORS["high"]
    elif score >= 25:
        return RISK_COLORS["medium"]
    return RISK_COLORS["low"]


def node_color(label: str) -> str:
    return NODE_COLORS.get(label, "#95A5A6")


def node_size(label: str) -> int:
    return NODE_SIZES.get(label, 15)


def edge_color(rel_type: str) -> str:
    return EDGE_COLORS.get(rel_type, EDGE_COLORS["DEFAULT"])

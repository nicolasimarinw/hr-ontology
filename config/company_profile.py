"""Meridian Technologies company profile for synthetic data generation."""

from datetime import date

COMPANY = {
    "name": "Meridian Technologies",
    "founded": date(2010, 3, 15),
    "industry": "Technology",
    "total_employees": 750,
    "annual_turnover_rate": 0.15,
    "data_start_date": date(2023, 1, 1),
    "data_end_date": date(2025, 12, 31),
}

LOCATIONS = [
    {"id": "LOC-001", "name": "San Francisco HQ", "city": "San Francisco", "country": "US", "is_hq": True},
    {"id": "LOC-002", "name": "New York Office", "city": "New York", "country": "US", "is_hq": False},
    {"id": "LOC-003", "name": "London Office", "city": "London", "country": "UK", "is_hq": False},
    {"id": "LOC-004", "name": "Remote", "city": "Remote", "country": "US", "is_hq": False},
]

# Location distribution weights
LOCATION_WEIGHTS = {
    "LOC-001": 0.40,  # 40% at HQ
    "LOC-002": 0.20,  # 20% NYC
    "LOC-003": 0.15,  # 15% London
    "LOC-004": 0.25,  # 25% Remote
}

DIVISIONS = [
    {"id": "DIV-ENG", "name": "Engineering"},
    {"id": "DIV-PROD", "name": "Product"},
    {"id": "DIV-SALES", "name": "Sales"},
    {"id": "DIV-OPS", "name": "Operations"},
    {"id": "DIV-CORP", "name": "Corporate"},
]

DEPARTMENTS = [
    # Engineering
    {"id": "DEPT-001", "name": "Backend Engineering", "division_id": "DIV-ENG", "headcount_pct": 0.12},
    {"id": "DEPT-002", "name": "Frontend Engineering", "division_id": "DIV-ENG", "headcount_pct": 0.10},
    {"id": "DEPT-003", "name": "Data Engineering", "division_id": "DIV-ENG", "headcount_pct": 0.06},
    {"id": "DEPT-004", "name": "DevOps & Infrastructure", "division_id": "DIV-ENG", "headcount_pct": 0.05},
    {"id": "DEPT-005", "name": "QA & Testing", "division_id": "DIV-ENG", "headcount_pct": 0.04},
    # Product
    {"id": "DEPT-006", "name": "Product Management", "division_id": "DIV-PROD", "headcount_pct": 0.05},
    {"id": "DEPT-007", "name": "UX Design", "division_id": "DIV-PROD", "headcount_pct": 0.04},
    {"id": "DEPT-008", "name": "Data Science & Analytics", "division_id": "DIV-PROD", "headcount_pct": 0.04},
    # Sales
    {"id": "DEPT-009", "name": "Enterprise Sales", "division_id": "DIV-SALES", "headcount_pct": 0.08},
    {"id": "DEPT-010", "name": "SMB Sales", "division_id": "DIV-SALES", "headcount_pct": 0.06},
    {"id": "DEPT-011", "name": "Sales Engineering", "division_id": "DIV-SALES", "headcount_pct": 0.04},
    {"id": "DEPT-012", "name": "Customer Success", "division_id": "DIV-SALES", "headcount_pct": 0.06},
    # Operations
    {"id": "DEPT-013", "name": "IT Operations", "division_id": "DIV-OPS", "headcount_pct": 0.04},
    {"id": "DEPT-014", "name": "Security", "division_id": "DIV-OPS", "headcount_pct": 0.03},
    {"id": "DEPT-015", "name": "Facilities & Office Management", "division_id": "DIV-OPS", "headcount_pct": 0.02},
    # Corporate
    {"id": "DEPT-016", "name": "Human Resources", "division_id": "DIV-CORP", "headcount_pct": 0.04},
    {"id": "DEPT-017", "name": "Finance & Accounting", "division_id": "DIV-CORP", "headcount_pct": 0.04},
    {"id": "DEPT-018", "name": "Legal & Compliance", "division_id": "DIV-CORP", "headcount_pct": 0.03},
    {"id": "DEPT-019", "name": "Marketing", "division_id": "DIV-CORP", "headcount_pct": 0.04},
    {"id": "DEPT-020", "name": "Executive Office", "division_id": "DIV-CORP", "headcount_pct": 0.02},
]

JOB_LEVELS = [
    {"id": "L1", "name": "Individual Contributor I", "rank": 1},
    {"id": "L2", "name": "Individual Contributor II", "rank": 2},
    {"id": "L3", "name": "Senior Individual Contributor", "rank": 3},
    {"id": "L4", "name": "Staff / Lead", "rank": 4},
    {"id": "M1", "name": "Manager", "rank": 5},
    {"id": "M2", "name": "Senior Manager", "rank": 6},
    {"id": "D1", "name": "Director", "rank": 7},
    {"id": "D2", "name": "Senior Director", "rank": 8},
    {"id": "VP", "name": "Vice President", "rank": 9},
    {"id": "CX", "name": "C-Suite", "rank": 10},
]

# Level distribution (approximate % of 750 employees)
LEVEL_DISTRIBUTION = {
    "L1": 0.20,
    "L2": 0.25,
    "L3": 0.20,
    "L4": 0.10,
    "M1": 0.10,
    "M2": 0.05,
    "D1": 0.04,
    "D2": 0.03,
    "VP": 0.02,
    "CX": 0.01,
}

JOB_FAMILIES = [
    {"id": "JF-ENG", "name": "Engineering"},
    {"id": "JF-PROD", "name": "Product"},
    {"id": "JF-DESIGN", "name": "Design"},
    {"id": "JF-DATA", "name": "Data & Analytics"},
    {"id": "JF-SALES", "name": "Sales"},
    {"id": "JF-CS", "name": "Customer Success"},
    {"id": "JF-MKTG", "name": "Marketing"},
    {"id": "JF-FIN", "name": "Finance"},
    {"id": "JF-HR", "name": "Human Resources"},
    {"id": "JF-LEGAL", "name": "Legal"},
    {"id": "JF-OPS", "name": "Operations"},
    {"id": "JF-EXEC", "name": "Executive"},
]

# Demographics distributions (US tech workforce approximation)
GENDER_DISTRIBUTION = {
    "Male": 0.58,
    "Female": 0.38,
    "Non-binary": 0.04,
}

ETHNICITY_DISTRIBUTION = {
    "White": 0.45,
    "Asian": 0.30,
    "Hispanic/Latino": 0.10,
    "Black/African American": 0.08,
    "Two or More Races": 0.05,
    "Other": 0.02,
}

# Skills catalog (core skills for MVP)
SKILL_CATALOG = [
    # Technical
    {"id": "SK-001", "name": "Python", "category": "Technical"},
    {"id": "SK-002", "name": "JavaScript", "category": "Technical"},
    {"id": "SK-003", "name": "SQL", "category": "Technical"},
    {"id": "SK-004", "name": "Cloud Architecture", "category": "Technical"},
    {"id": "SK-005", "name": "Machine Learning", "category": "Technical"},
    {"id": "SK-006", "name": "System Design", "category": "Technical"},
    {"id": "SK-007", "name": "API Design", "category": "Technical"},
    {"id": "SK-008", "name": "Data Modeling", "category": "Technical"},
    {"id": "SK-009", "name": "DevOps", "category": "Technical"},
    {"id": "SK-010", "name": "Security Engineering", "category": "Technical"},
    # Product & Design
    {"id": "SK-011", "name": "Product Strategy", "category": "Product"},
    {"id": "SK-012", "name": "User Research", "category": "Product"},
    {"id": "SK-013", "name": "UX Design", "category": "Design"},
    {"id": "SK-014", "name": "Data Analysis", "category": "Data"},
    {"id": "SK-015", "name": "A/B Testing", "category": "Data"},
    # Business
    {"id": "SK-016", "name": "Sales Strategy", "category": "Business"},
    {"id": "SK-017", "name": "Account Management", "category": "Business"},
    {"id": "SK-018", "name": "Financial Analysis", "category": "Business"},
    {"id": "SK-019", "name": "Contract Negotiation", "category": "Business"},
    {"id": "SK-020", "name": "Project Management", "category": "Business"},
    # Leadership
    {"id": "SK-021", "name": "People Management", "category": "Leadership"},
    {"id": "SK-022", "name": "Strategic Planning", "category": "Leadership"},
    {"id": "SK-023", "name": "Cross-functional Collaboration", "category": "Leadership"},
    {"id": "SK-024", "name": "Stakeholder Management", "category": "Leadership"},
    {"id": "SK-025", "name": "Change Management", "category": "Leadership"},
]

# Termination reasons
TERMINATION_REASONS = {
    "Voluntary - Better Opportunity": 0.35,
    "Voluntary - Relocation": 0.10,
    "Voluntary - Career Change": 0.10,
    "Voluntary - Compensation": 0.15,
    "Voluntary - Work-Life Balance": 0.10,
    "Involuntary - Performance": 0.10,
    "Involuntary - Restructuring": 0.05,
    "Involuntary - Policy Violation": 0.03,
    "Retirement": 0.02,
}

# Recruiting sources
CANDIDATE_SOURCES = {
    "LinkedIn": 0.30,
    "Employee Referral": 0.25,
    "Job Board (Indeed)": 0.15,
    "Job Board (Glassdoor)": 0.08,
    "Company Website": 0.10,
    "Recruiter": 0.07,
    "University/Campus": 0.05,
}

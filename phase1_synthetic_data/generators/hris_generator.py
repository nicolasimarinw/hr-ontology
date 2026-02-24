"""Core HRIS generator: employees, departments, positions, org hierarchy, employment history."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from config.company_profile import (
    COMPANY, DEPARTMENTS, DIVISIONS, ETHNICITY_DISTRIBUTION,
    GENDER_DISTRIBUTION, JOB_FAMILIES, JOB_LEVELS, LEVEL_DISTRIBUTION,
    LOCATION_WEIGHTS, LOCATIONS, SKILL_CATALOG, TERMINATION_REASONS,
)
from phase1_synthetic_data.generators.base_generator import BaseGenerator
from phase1_synthetic_data.generators.distributions import (
    birth_date_from_age, exponential_tenure, random_date_between, weighted_choice,
)
from phase1_synthetic_data.generators.shared_state import (
    Department, Employee, Position, SharedState,
)
from phase1_synthetic_data.generators.temporal import generate_event_timeline


fake = Faker()
Faker.seed(42)

# Map departments to their primary job family
DEPT_TO_JOB_FAMILY = {
    "DEPT-001": "JF-ENG", "DEPT-002": "JF-ENG", "DEPT-003": "JF-DATA",
    "DEPT-004": "JF-ENG", "DEPT-005": "JF-ENG",
    "DEPT-006": "JF-PROD", "DEPT-007": "JF-DESIGN", "DEPT-008": "JF-DATA",
    "DEPT-009": "JF-SALES", "DEPT-010": "JF-SALES", "DEPT-011": "JF-SALES",
    "DEPT-012": "JF-CS",
    "DEPT-013": "JF-OPS", "DEPT-014": "JF-OPS", "DEPT-015": "JF-OPS",
    "DEPT-016": "JF-HR", "DEPT-017": "JF-FIN", "DEPT-018": "JF-LEGAL",
    "DEPT-019": "JF-MKTG", "DEPT-020": "JF-EXEC",
}

# Job title templates per family and level
TITLE_TEMPLATES = {
    "JF-ENG": {
        "L1": "Software Engineer I", "L2": "Software Engineer II",
        "L3": "Senior Software Engineer", "L4": "Staff Engineer",
        "M1": "Engineering Manager", "M2": "Senior Engineering Manager",
        "D1": "Director of Engineering", "D2": "Senior Director of Engineering",
        "VP": "VP of Engineering", "CX": "CTO",
    },
    "JF-PROD": {
        "L1": "Associate Product Manager", "L2": "Product Manager",
        "L3": "Senior Product Manager", "L4": "Principal Product Manager",
        "M1": "Product Lead", "M2": "Senior Product Lead",
        "D1": "Director of Product", "D2": "Senior Director of Product",
        "VP": "VP of Product", "CX": "CPO",
    },
    "JF-DESIGN": {
        "L1": "UX Designer I", "L2": "UX Designer II",
        "L3": "Senior UX Designer", "L4": "Staff Designer",
        "M1": "Design Manager", "M2": "Senior Design Manager",
        "D1": "Director of Design", "D2": "Senior Director of Design",
        "VP": "VP of Design", "CX": "Chief Design Officer",
    },
    "JF-DATA": {
        "L1": "Data Analyst I", "L2": "Data Analyst II",
        "L3": "Senior Data Scientist", "L4": "Staff Data Scientist",
        "M1": "Data Science Manager", "M2": "Senior Data Manager",
        "D1": "Director of Data", "D2": "Senior Director of Data",
        "VP": "VP of Data", "CX": "Chief Data Officer",
    },
    "JF-SALES": {
        "L1": "Sales Development Rep", "L2": "Account Executive",
        "L3": "Senior Account Executive", "L4": "Enterprise Account Executive",
        "M1": "Sales Manager", "M2": "Senior Sales Manager",
        "D1": "Director of Sales", "D2": "Senior Director of Sales",
        "VP": "VP of Sales", "CX": "CRO",
    },
    "JF-CS": {
        "L1": "Customer Success Associate", "L2": "Customer Success Manager",
        "L3": "Senior CSM", "L4": "Principal CSM",
        "M1": "CS Team Lead", "M2": "Senior CS Manager",
        "D1": "Director of CS", "D2": "Senior Director of CS",
        "VP": "VP of Customer Success", "CX": "Chief Customer Officer",
    },
    "JF-MKTG": {
        "L1": "Marketing Coordinator", "L2": "Marketing Specialist",
        "L3": "Senior Marketing Manager", "L4": "Principal Marketer",
        "M1": "Marketing Manager", "M2": "Senior Marketing Manager",
        "D1": "Director of Marketing", "D2": "Senior Director of Marketing",
        "VP": "VP of Marketing", "CX": "CMO",
    },
    "JF-FIN": {
        "L1": "Financial Analyst I", "L2": "Financial Analyst II",
        "L3": "Senior Financial Analyst", "L4": "Principal Analyst",
        "M1": "Finance Manager", "M2": "Senior Finance Manager",
        "D1": "Director of Finance", "D2": "Senior Director of Finance",
        "VP": "VP of Finance", "CX": "CFO",
    },
    "JF-HR": {
        "L1": "HR Coordinator", "L2": "HR Generalist",
        "L3": "Senior HR Business Partner", "L4": "Principal HRBP",
        "M1": "HR Manager", "M2": "Senior HR Manager",
        "D1": "Director of HR", "D2": "Senior Director of HR",
        "VP": "VP of People", "CX": "CHRO",
    },
    "JF-LEGAL": {
        "L1": "Legal Assistant", "L2": "Paralegal",
        "L3": "Senior Counsel", "L4": "Principal Counsel",
        "M1": "Legal Manager", "M2": "Senior Legal Manager",
        "D1": "Director of Legal", "D2": "Senior Director of Legal",
        "VP": "VP of Legal", "CX": "General Counsel",
    },
    "JF-OPS": {
        "L1": "Operations Analyst I", "L2": "Operations Analyst II",
        "L3": "Senior Operations Analyst", "L4": "Staff Operations",
        "M1": "Operations Manager", "M2": "Senior Operations Manager",
        "D1": "Director of Operations", "D2": "Senior Director of Operations",
        "VP": "VP of Operations", "CX": "COO",
    },
    "JF-EXEC": {
        "L1": "Executive Assistant", "L2": "Senior Executive Assistant",
        "L3": "Chief of Staff", "L4": "Senior Chief of Staff",
        "M1": "Office Manager", "M2": "Senior Office Manager",
        "D1": "Director of Strategy", "D2": "Senior Director of Strategy",
        "VP": "VP of Strategy", "CX": "CEO",
    },
}


class HRISGenerator(BaseGenerator):
    name = "hris"

    def generate(self) -> None:
        rng = self.state.rng

        # Load skill catalog into shared state
        self.state.skill_catalog = SKILL_CATALOG

        # 1. Create departments
        self._generate_departments()

        # 2. Determine headcount per department and level
        allocations = self._compute_headcount_allocations(rng)

        # 3. Generate the CEO first
        ceo = self._generate_ceo(rng)

        # 4. Generate VPs (one per division)
        vps = self._generate_vps(rng, ceo)

        # 5. Generate Directors, Managers, and ICs top-down
        self._generate_org_tree(rng, vps, allocations)

        # 6. Apply terminations to ~15% of historical employees
        self._apply_terminations(rng)

        # 7. Generate employment history events
        history_rows = self._generate_employment_history(rng)

        # 8. Build DataFrames
        self._build_dataframes(history_rows)

    def _generate_departments(self) -> None:
        for dept_cfg in DEPARTMENTS:
            dept = Department(
                dept_id=dept_cfg["id"],
                name=dept_cfg["name"],
                division_id=dept_cfg["division_id"],
            )
            self.state.register_department(dept)

    def _compute_headcount_allocations(self, rng: np.random.Generator) -> list[dict]:
        """Compute how many people at each level go into each department."""
        target_total = COMPANY["total_employees"]
        allocations = []

        for dept_cfg in DEPARTMENTS:
            dept_headcount = max(2, int(target_total * dept_cfg["headcount_pct"]))
            for level_id, level_pct in LEVEL_DISTRIBUTION.items():
                count = max(0, round(dept_headcount * level_pct))
                if count > 0:
                    allocations.append({
                        "dept_id": dept_cfg["id"],
                        "level": level_id,
                        "count": count,
                    })

        return allocations

    def _generate_ceo(self, rng: np.random.Generator) -> Employee:
        job_family = "JF-EXEC"
        job_level = "CX"
        dept_id = "DEPT-020"  # Executive Office

        pos = Position(
            position_id=self.state.next_id("POS"),
            title="Chief Executive Officer",
            job_family=job_family,
            job_level=job_level,
            department_id=dept_id,
        )
        self.state.register_position(pos)

        hire_date = COMPANY["founded"]
        emp = self._create_employee(
            rng, pos, dept_id, job_family, job_level, hire_date, manager_id=None,
        )
        self.state.register_employee(emp)
        self.state.departments[dept_id].head_id = emp.employee_id
        return emp

    def _generate_vps(self, rng: np.random.Generator, ceo: Employee) -> list[Employee]:
        vps = []
        for div in DIVISIONS:
            # Find a department in this division to assign the VP
            div_depts = [d for d in DEPARTMENTS if d["division_id"] == div["id"]]
            primary_dept = div_depts[0]["id"]
            job_family = DEPT_TO_JOB_FAMILY.get(primary_dept, "JF-EXEC")

            title = TITLE_TEMPLATES.get(job_family, {}).get("VP", f"VP of {div['name']}")
            pos = Position(
                position_id=self.state.next_id("POS"),
                title=title,
                job_family=job_family,
                job_level="VP",
                department_id=primary_dept,
            )
            self.state.register_position(pos)

            # VPs hired within first 2 years of company
            hire_date = random_date_between(
                rng, COMPANY["founded"], COMPANY["founded"] + timedelta(days=730)
            )[0]
            emp = self._create_employee(
                rng, pos, primary_dept, job_family, "VP", hire_date,
                manager_id=ceo.employee_id,
            )
            self.state.register_employee(emp)
            vps.append(emp)

        return vps

    def _generate_org_tree(
        self, rng: np.random.Generator, vps: list[Employee], allocations: list[dict],
    ) -> None:
        """Generate Directors, Managers, and ICs hierarchically."""

        # Group allocations by department
        dept_allocs: dict[str, dict[str, int]] = {}
        for alloc in allocations:
            dept_allocs.setdefault(alloc["dept_id"], {})[alloc["level"]] = alloc["count"]

        # For each department, find its VP (via division)
        dept_to_vp: dict[str, Employee] = {}
        for dept_cfg in DEPARTMENTS:
            div_id = dept_cfg["division_id"]
            for vp in vps:
                vp_dept = self.state.departments[vp.department_id]
                if vp_dept.division_id == div_id:
                    dept_to_vp[dept_cfg["id"]] = vp
                    break

        # Generate top-down per department: D2 -> D1 -> M2 -> M1 -> L4 -> L3 -> L2 -> L1
        level_order = ["D2", "D1", "M2", "M1", "L4", "L3", "L2", "L1"]

        for dept_cfg in DEPARTMENTS:
            dept_id = dept_cfg["id"]
            levels = dept_allocs.get(dept_id, {})
            job_family = DEPT_TO_JOB_FAMILY.get(dept_id, "JF-OPS")

            # Manager hierarchy within this department
            current_managers = []
            vp = dept_to_vp.get(dept_id)
            if vp:
                current_managers = [vp]

            for level in level_order:
                count = levels.get(level, 0)
                if count == 0:
                    continue

                level_employees = []
                for _ in range(count):
                    # Pick a manager from current_managers (or VP if none)
                    if current_managers:
                        manager = rng.choice(current_managers)
                        manager_id = manager.employee_id
                    elif vp:
                        manager_id = vp.employee_id
                    else:
                        manager_id = None

                    title = TITLE_TEMPLATES.get(job_family, {}).get(level, f"{level} - {dept_cfg['name']}")
                    pos = Position(
                        position_id=self.state.next_id("POS"),
                        title=title,
                        job_family=job_family,
                        job_level=level,
                        department_id=dept_id,
                    )
                    self.state.register_position(pos)

                    # Tenure-based hire date
                    tenure_years = exponential_tenure(rng, scale=3.3, max_years=12.0)[0]
                    hire_date = COMPANY["data_end_date"] - timedelta(days=int(tenure_years * 365.25))
                    hire_date = max(hire_date, COMPANY["founded"])

                    emp = self._create_employee(
                        rng, pos, dept_id, job_family, level, hire_date, manager_id,
                    )
                    self.state.register_employee(emp)
                    level_employees.append(emp)

                # People at manager+ levels become managers for next level down
                if level.startswith("D") or level.startswith("M"):
                    current_managers = level_employees if level_employees else current_managers

    def _create_employee(
        self, rng: np.random.Generator, pos: Position, dept_id: str,
        job_family: str, job_level: str, hire_date: date, manager_id: str | None,
    ) -> Employee:
        gender = weighted_choice(rng, GENDER_DISTRIBUTION)[0]
        ethnicity = weighted_choice(rng, ETHNICITY_DISTRIBUTION)[0]
        location_id = weighted_choice(rng, LOCATION_WEIGHTS)[0]
        birth_date = birth_date_from_age(rng, hire_date, mean_age=35, std_age=9)[0]

        first_name = fake.first_name_male() if gender == "Male" else fake.first_name_female()
        if gender == "Non-binary":
            first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{first_name.lower()}.{last_name.lower()}@meridiantech.com"

        emp_id = self.state.next_id("EMP")

        return Employee(
            employee_id=emp_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            hire_date=hire_date,
            birth_date=birth_date,
            gender=gender,
            ethnicity=ethnicity,
            location_id=location_id,
            department_id=dept_id,
            position_id=pos.position_id,
            manager_id=manager_id,
            job_level=job_level,
            job_family=job_family,
        )

    def _apply_terminations(self, rng: np.random.Generator) -> None:
        """Mark ~15% of employees as terminated with realistic patterns."""
        all_emps = list(self.state.employees.values())
        # Don't terminate the CEO or VPs
        eligible = [e for e in all_emps if e.job_level not in ("CX", "VP")]

        target_terms = int(len(all_emps) * COMPANY["annual_turnover_rate"] * 3)  # 3 years of data
        # But cap at a reasonable fraction
        target_terms = min(target_terms, int(len(eligible) * 0.30))

        term_indices = rng.choice(len(eligible), size=target_terms, replace=False)

        for idx in term_indices:
            emp = eligible[idx]
            # Termination date: between hire + 90 days and data_end_date
            earliest_term = emp.hire_date + timedelta(days=90)
            if earliest_term >= COMPANY["data_end_date"]:
                continue
            term_date = random_date_between(rng, earliest_term, COMPANY["data_end_date"])[0]
            reason = weighted_choice(rng, TERMINATION_REASONS)[0]

            emp.status = "Terminated"
            emp.termination_date = term_date
            emp.termination_reason = reason

    def _generate_employment_history(self, rng: np.random.Generator) -> list[dict]:
        """Generate employment history events (promotions, transfers)."""
        history = []

        for emp in self.state.employees.values():
            # Hire event
            history.append({
                "employee_id": emp.employee_id,
                "event_type": "Hire",
                "effective_date": emp.hire_date,
                "from_position": None,
                "to_position": emp.position_id,
                "from_department": None,
                "to_department": emp.department_id,
            })

            # Generate promotions/transfers for tenured employees
            end = emp.termination_date or COMPANY["data_end_date"]
            events = generate_event_timeline(
                rng, emp.hire_date, end,
                event_types=["Promotion", "Transfer"],
                avg_events_per_year=0.2,
                min_gap_days=180,
            )
            for event in events:
                history.append({
                    "employee_id": emp.employee_id,
                    "event_type": event["event_type"],
                    "effective_date": event["date"],
                    "from_position": emp.position_id,
                    "to_position": emp.position_id,  # simplified for MVP
                    "from_department": emp.department_id,
                    "to_department": emp.department_id,
                })

            # Termination event
            if emp.status == "Terminated":
                history.append({
                    "employee_id": emp.employee_id,
                    "event_type": "Termination",
                    "effective_date": emp.termination_date,
                    "from_position": emp.position_id,
                    "to_position": None,
                    "from_department": emp.department_id,
                    "to_department": None,
                })

        return history

    def _build_dataframes(self, history_rows: list[dict]) -> None:
        # Employees
        emp_rows = []
        for emp in self.state.employees.values():
            emp_rows.append({
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "email": emp.email,
                "hire_date": emp.hire_date,
                "birth_date": emp.birth_date,
                "gender": emp.gender,
                "ethnicity": emp.ethnicity,
                "location_id": emp.location_id,
                "department_id": emp.department_id,
                "position_id": emp.position_id,
                "manager_id": emp.manager_id,
                "job_level": emp.job_level,
                "job_family": emp.job_family,
                "status": emp.status,
                "termination_date": emp.termination_date,
                "termination_reason": emp.termination_reason,
            })
        self.register("employees", pd.DataFrame(emp_rows))

        # Departments
        dept_rows = []
        for dept in self.state.departments.values():
            div_name = next(
                (d["name"] for d in DIVISIONS if d["id"] == dept.division_id), None
            )
            dept_rows.append({
                "dept_id": dept.dept_id,
                "name": dept.name,
                "division_id": dept.division_id,
                "division_name": div_name,
                "head_id": dept.head_id,
            })
        self.register("departments", pd.DataFrame(dept_rows))

        # Positions
        pos_rows = []
        for pos in self.state.positions.values():
            pos_rows.append({
                "position_id": pos.position_id,
                "title": pos.title,
                "job_family": pos.job_family,
                "job_level": pos.job_level,
                "department_id": pos.department_id,
            })
        self.register("positions", pd.DataFrame(pos_rows))

        # Locations
        self.register("locations", pd.DataFrame(LOCATIONS))

        # Employment history
        self.register("employment_history", pd.DataFrame(history_rows))

    def validate(self) -> list[str]:
        errors = super().validate()

        employees_df = self._dataframes.get("employees")
        if employees_df is not None:
            # Check manager references
            emp_ids = set(employees_df["employee_id"])
            mgr_ids = set(employees_df["manager_id"].dropna())
            orphan_mgrs = mgr_ids - emp_ids
            if orphan_mgrs:
                errors.append(f"Orphan manager IDs: {orphan_mgrs}")

            # Check no hire dates before company founding
            early_hires = employees_df[employees_df["hire_date"] < COMPANY["founded"]]
            if len(early_hires) > 0:
                errors.append(f"{len(early_hires)} employees hired before company founding")

            # Check termination dates after hire dates
            termed = employees_df[employees_df["termination_date"].notna()]
            bad_terms = termed[termed["termination_date"] < termed["hire_date"]]
            if len(bad_terms) > 0:
                errors.append(f"{len(bad_terms)} employees terminated before hire date")

        return errors

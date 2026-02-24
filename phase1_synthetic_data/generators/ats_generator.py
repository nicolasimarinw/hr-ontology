"""ATS generator: requisitions, candidates, applications, interviews, offers."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from config.company_profile import CANDIDATE_SOURCES, COMPANY, DEPARTMENTS
from phase1_synthetic_data.generators.base_generator import BaseGenerator
from phase1_synthetic_data.generators.distributions import (
    random_date_between, weighted_choice,
)
from phase1_synthetic_data.generators.shared_state import SharedState
from phase1_synthetic_data.generators.temporal import add_business_days

fake = Faker()
Faker.seed(43)

INTERVIEW_TYPES = ["Phone Screen", "Technical", "Behavioral", "Panel", "Final"]

APPLICATION_STAGES = [
    "Applied", "Screened", "Phone Interview", "Technical Interview",
    "Onsite Interview", "Offer", "Hired", "Rejected", "Withdrawn",
]


class ATSGenerator(BaseGenerator):
    name = "ats"

    def generate(self) -> None:
        rng = self.state.rng

        # Generate requisitions for every hired employee + some open/cancelled reqs
        requisitions = []
        candidates = []
        applications = []
        interviews = []
        offers = []

        seen_candidate_emails = set()

        # 1. Create requisitions for filled positions (every current employee was hired via a req)
        all_employees = list(self.state.employees.values())
        # Sample ~60% of employees to have recruiting history (others were hired pre-ATS)
        tracked_employees = [e for e in all_employees if rng.random() < 0.60]

        for emp in tracked_employees:
            pos = self.state.positions.get(emp.position_id)
            if not pos:
                continue

            # Requisition opened ~60 days before hire
            req_open = emp.hire_date - timedelta(days=int(rng.integers(30, 90)))
            req_close = emp.hire_date + timedelta(days=int(rng.integers(1, 14)))

            req_id = self.state.next_id("REQ")
            requisitions.append({
                "req_id": req_id,
                "title": pos.title,
                "department_id": pos.department_id,
                "hiring_manager_id": emp.manager_id,
                "open_date": req_open,
                "close_date": req_close,
                "status": "Filled",
                "headcount": 1,
            })

            # Generate 5-20 candidates per req
            num_candidates = int(rng.integers(5, 21))
            hired_candidate_id = None

            for c_idx in range(num_candidates):
                cand_id = self.state.next_id("CAND")
                is_hired = (c_idx == 0)  # First candidate is the one who got hired

                if is_hired:
                    hired_candidate_id = cand_id
                    cand_name = f"{emp.first_name} {emp.last_name}"
                    cand_email = emp.email
                else:
                    cand_first = fake.first_name()
                    cand_last = fake.last_name()
                    cand_name = f"{cand_first} {cand_last}"
                    cand_email = f"{cand_first.lower()}.{cand_last.lower()}@{fake.free_email_domain()}"
                    # Avoid duplicate emails
                    while cand_email in seen_candidate_emails:
                        cand_last = fake.last_name()
                        cand_email = f"{cand_first.lower()}.{cand_last.lower()}@{fake.free_email_domain()}"

                seen_candidate_emails.add(cand_email)
                source = weighted_choice(rng, CANDIDATE_SOURCES)[0]

                candidates.append({
                    "candidate_id": cand_id,
                    "name": cand_name,
                    "email": cand_email,
                    "source": source,
                })

                # Application
                apply_date = random_date_between(rng, req_open, req_open + timedelta(days=30))[0]
                app_id = self.state.next_id("APP")

                if is_hired:
                    app_status = "Hired"
                    app_stage = "Hired"
                else:
                    # Funnel: most rejected at screening, fewer at each stage
                    rejection_probs = {
                        "Screened": 0.40,
                        "Phone Interview": 0.25,
                        "Technical Interview": 0.20,
                        "Onsite Interview": 0.10,
                        "Withdrawn": 0.05,
                    }
                    app_stage = weighted_choice(rng, rejection_probs)[0]
                    app_status = "Withdrawn" if app_stage == "Withdrawn" else "Rejected"

                applications.append({
                    "application_id": app_id,
                    "candidate_id": cand_id,
                    "req_id": req_id,
                    "apply_date": apply_date,
                    "status": app_status,
                    "stage": app_stage,
                })

                # Interviews (hired candidates get all rounds, others vary by stage)
                stage_to_interviews = {
                    "Screened": ["Phone Screen"],
                    "Phone Interview": ["Phone Screen"],
                    "Technical Interview": ["Phone Screen", "Technical"],
                    "Onsite Interview": ["Phone Screen", "Technical", "Behavioral"],
                    "Hired": ["Phone Screen", "Technical", "Behavioral", "Panel", "Final"],
                    "Withdrawn": [],
                }
                interview_types = stage_to_interviews.get(app_stage, [])

                # Pick interviewers from active employees in the department
                dept_emps = [e for e in self.state.active_employees()
                             if e.department_id == pos.department_id
                             and e.employee_id != emp.employee_id]

                current_date = apply_date + timedelta(days=3)
                for itype in interview_types:
                    interviewer = None
                    if dept_emps:
                        interviewer = rng.choice(dept_emps)

                    # Score: hired candidates score higher on average
                    if is_hired:
                        score = round(float(rng.uniform(3.5, 5.0)), 1)
                    else:
                        score = round(float(rng.uniform(1.5, 4.5)), 1)

                    interviews.append({
                        "interview_id": self.state.next_id("INT"),
                        "application_id": app_id,
                        "interviewer_id": interviewer.employee_id if interviewer else None,
                        "date": current_date,
                        "type": itype,
                        "score": score,
                        "feedback": _generate_feedback(rng, score),
                    })
                    current_date = add_business_days(current_date, rng.integers(2, 7))

                # Offer for hired candidate
                if is_hired:
                    offer_date = current_date + timedelta(days=int(rng.integers(1, 5)))
                    offers.append({
                        "offer_id": self.state.next_id("OFR"),
                        "application_id": app_id,
                        "salary_offered": _estimate_offer_salary(rng, emp.job_level, emp.job_family),
                        "equity_offered": int(rng.integers(0, 2000)) if emp.job_level in ("L4", "M1", "M2", "D1", "D2", "VP", "CX") else 0,
                        "status": "Accepted",
                        "offer_date": offer_date,
                        "response_date": offer_date + timedelta(days=int(rng.integers(1, 7))),
                        "start_date": emp.hire_date,
                    })

        # 2. Add some currently open requisitions
        for _ in range(int(rng.integers(10, 25))):
            dept = rng.choice(DEPARTMENTS)
            req_id = self.state.next_id("REQ")
            open_date = random_date_between(
                rng, COMPANY["data_end_date"] - timedelta(days=60), COMPANY["data_end_date"]
            )[0]
            requisitions.append({
                "req_id": req_id,
                "title": f"Open Role - {dept['name']}",
                "department_id": dept["id"],
                "hiring_manager_id": None,
                "open_date": open_date,
                "close_date": None,
                "status": "Open",
                "headcount": 1,
            })

        self.register("requisitions", pd.DataFrame(requisitions))
        self.register("candidates", pd.DataFrame(candidates))
        self.register("applications", pd.DataFrame(applications))
        self.register("interviews", pd.DataFrame(interviews))
        self.register("offers", pd.DataFrame(offers))

    def validate(self) -> list[str]:
        errors = super().validate()

        apps_df = self._dataframes.get("applications")
        reqs_df = self._dataframes.get("requisitions")

        if apps_df is not None and reqs_df is not None:
            # All application req_ids should exist in requisitions
            req_ids = set(reqs_df["req_id"])
            app_req_ids = set(apps_df["req_id"])
            orphans = app_req_ids - req_ids
            if orphans:
                errors.append(f"{len(orphans)} applications reference non-existent requisitions")

        return errors


def _generate_feedback(rng: np.random.Generator, score: float) -> str:
    """Generate simple interview feedback based on score."""
    if score >= 4.0:
        return rng.choice([
            "Strong candidate. Excellent technical depth.",
            "Very impressive. Clear communicator with strong problem-solving.",
            "Highly recommend. Great culture fit and technical skills.",
            "Outstanding performance in the interview. Hire recommendation.",
        ])
    elif score >= 3.0:
        return rng.choice([
            "Solid candidate. Some areas could be stronger.",
            "Good potential but needs more experience in key areas.",
            "Meets requirements but didn't stand out.",
            "Acceptable performance. Consider for the role.",
        ])
    else:
        return rng.choice([
            "Below expectations. Struggled with core concepts.",
            "Not a fit for this role at this time.",
            "Significant gaps in required skills.",
            "Would not recommend moving forward.",
        ])


def _estimate_offer_salary(
    rng: np.random.Generator, job_level: str, job_family: str,
) -> int:
    """Estimate an offer salary for a given level and family."""
    from phase1_synthetic_data.generators.compensation_generator import (
        FAMILY_MULTIPLIERS, LEVEL_MIDPOINTS,
    )
    midpoint = LEVEL_MIDPOINTS.get(job_level, 100_000)
    mult = FAMILY_MULTIPLIERS.get(job_family, 1.0)
    base = midpoint * mult
    # Offers typically at 90-105% of midpoint
    return round(base * rng.uniform(0.90, 1.05) / 1000) * 1000

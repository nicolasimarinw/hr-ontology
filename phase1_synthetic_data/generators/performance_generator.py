"""Performance Management generator: cycles, goals, reviews, ratings, competency assessments."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from config.company_profile import COMPANY, SKILL_CATALOG
from phase1_synthetic_data.generators.base_generator import BaseGenerator
from phase1_synthetic_data.generators.distributions import beta_rating
from phase1_synthetic_data.generators.shared_state import SharedState
from phase1_synthetic_data.generators.temporal import generate_review_dates

fake = Faker()
Faker.seed(44)

# Goal templates by job family
GOAL_TEMPLATES = {
    "JF-ENG": [
        "Deliver {feature} by end of {period}",
        "Reduce system latency by {pct}%",
        "Improve code coverage to {pct}%",
        "Lead architecture review for {component}",
        "Mentor {count} junior engineers",
    ],
    "JF-PROD": [
        "Launch {feature} to {pct}% of users",
        "Increase user engagement by {pct}%",
        "Complete competitive analysis for {domain}",
        "Define and validate product roadmap for {period}",
    ],
    "JF-SALES": [
        "Achieve {pct}% of quarterly quota",
        "Close {count} enterprise deals",
        "Expand existing accounts by {pct}%",
        "Build pipeline of ${amount}M",
    ],
    "default": [
        "Complete {project} initiative by {period}",
        "Improve team process efficiency by {pct}%",
        "Develop expertise in {skill}",
        "Successfully onboard {count} new team members",
    ],
}

STRENGTHS = [
    "Strong technical skills and problem-solving ability",
    "Excellent communication and collaboration",
    "Consistent delivery against deadlines",
    "Proactive approach to identifying issues",
    "Great mentoring and team building",
    "Creative thinking and innovation",
    "Strong attention to detail",
    "Effective stakeholder management",
    "Demonstrated leadership in cross-functional projects",
    "Deep domain expertise and knowledge sharing",
]

DEVELOPMENT_AREAS = [
    "Could improve documentation practices",
    "Should focus on broader strategic thinking",
    "Needs to delegate more effectively",
    "Would benefit from stronger presentation skills",
    "Should seek more cross-functional exposure",
    "Could improve time management and prioritization",
    "Needs more experience with system design at scale",
    "Should develop stronger data-driven decision making",
    "Would benefit from more proactive communication",
    "Needs to build stronger external network",
]


class PerformanceGenerator(BaseGenerator):
    name = "performance"

    def generate(self) -> None:
        rng = self.state.rng

        # 1. Generate performance cycles
        cycles = self._generate_cycles()

        # 2. Generate goals for each employee per cycle
        goals = self._generate_goals(rng, cycles)

        # 3. Generate performance reviews
        reviews = self._generate_reviews(rng, cycles)

        # 4. Generate competency assessments
        assessments = self._generate_competency_assessments(rng, cycles)

        self.register("performance_cycles", pd.DataFrame(cycles))
        self.register("goals", pd.DataFrame(goals))
        self.register("performance_reviews", pd.DataFrame(reviews))
        self.register("competency_assessments", pd.DataFrame(assessments))

    def _generate_cycles(self) -> list[dict]:
        """Generate semi-annual review cycles over the data period."""
        cycles = []
        review_dates = generate_review_dates(
            COMPANY["data_start_date"], COMPANY["data_end_date"], "semi-annual"
        )

        for i, end_date in enumerate(review_dates):
            cycle_id = f"CYCLE-{i+1:03d}"
            if end_date.month == 6:
                start = date(end_date.year, 1, 1)
                name = f"H1 {end_date.year}"
                cycle_type = "Semi-annual"
            else:
                start = date(end_date.year, 7, 1)
                name = f"H2 {end_date.year}"
                cycle_type = "Semi-annual"

            cycles.append({
                "cycle_id": cycle_id,
                "name": name,
                "start_date": start,
                "end_date": end_date,
                "type": cycle_type,
            })

        return cycles

    def _generate_goals(self, rng: np.random.Generator, cycles: list[dict]) -> list[dict]:
        """Generate 2-5 goals per employee per cycle they were active."""
        rows = []

        for cycle in cycles:
            cycle_start = cycle["start_date"]
            cycle_end = cycle["end_date"]

            active_emps = self.state.active_employees_at(cycle_end)

            for emp in active_emps:
                # Skip if hired after cycle midpoint
                cycle_mid = cycle_start + (cycle_end - cycle_start) / 2
                if emp.hire_date > cycle_mid:
                    continue

                num_goals = int(rng.integers(2, 6))
                templates = GOAL_TEMPLATES.get(emp.job_family, GOAL_TEMPLATES["default"])

                for g in range(num_goals):
                    template = rng.choice(templates)
                    title = template.format(
                        feature=fake.catch_phrase(),
                        period=cycle["name"],
                        pct=rng.integers(10, 50),
                        component=fake.word().capitalize(),
                        count=rng.integers(1, 5),
                        project=fake.bs().title(),
                        skill=rng.choice(SKILL_CATALOG)["name"],
                        domain=fake.word().capitalize(),
                        amount=rng.integers(1, 10),
                    )

                    # Achievement: correlated with performance (will be set in reviews)
                    achievement = float(rng.uniform(0.3, 1.0))
                    status = "Completed" if achievement > 0.7 else "In Progress" if achievement > 0.4 else "At Risk"

                    weight = round(1.0 / num_goals, 2)

                    rows.append({
                        "goal_id": self.state.next_id("GOAL"),
                        "employee_id": emp.employee_id,
                        "cycle_id": cycle["cycle_id"],
                        "title": title,
                        "description": f"Goal for {cycle['name']}: {title}",
                        "status": status,
                        "weight": weight,
                        "achievement_pct": round(achievement * 100, 1),
                    })

        return rows

    def _generate_reviews(self, rng: np.random.Generator, cycles: list[dict]) -> list[dict]:
        """Generate performance reviews with ratings that embed realistic biases."""
        rows = []

        for cycle in cycles:
            cycle_end = cycle["end_date"]
            active_emps = self.state.active_employees_at(cycle_end)

            for emp in active_emps:
                # Skip very new employees
                if emp.hire_date > cycle_end - timedelta(days=60):
                    continue

                # Base rating from beta distribution (right-skewed, most people 3-4.5)
                base_rating = float(beta_rating(rng, alpha=5.0, beta=2.0, low=1.0, high=5.0)[0])

                # Embed subtle biases for analytics to discover:
                # - Slight rating penalty for underrepresented groups
                gender_adj = {"Male": 0.0, "Female": -0.15, "Non-binary": -0.10}.get(emp.gender, 0.0)
                ethnicity_adj = {
                    "White": 0.0, "Asian": 0.05,
                    "Black/African American": -0.15,
                    "Hispanic/Latino": -0.10,
                    "Two or More Races": -0.05,
                    "Other": -0.05,
                }.get(emp.ethnicity, 0.0)

                # Manager quality effect (proxy: managers with many reports give lower ratings)
                num_reports = len(self.state.direct_reports(emp.manager_id)) if emp.manager_id else 0
                span_adj = -0.1 if num_reports > 10 else 0.0

                # Tenure boost (tenured employees tend to rate slightly higher)
                tenure_years = (cycle_end - emp.hire_date).days / 365.25
                tenure_adj = min(tenure_years * 0.05, 0.2)

                # Final rating with noise
                noise = float(rng.normal(0, 0.2))
                rating = base_rating + gender_adj + ethnicity_adj + span_adj + tenure_adj + noise
                rating = round(max(1.0, min(5.0, rating)), 1)

                # Select strengths and development areas
                num_strengths = rng.integers(1, 4)
                num_dev = rng.integers(1, 3)
                strengths = rng.choice(STRENGTHS, size=num_strengths, replace=False).tolist()
                dev_areas = rng.choice(DEVELOPMENT_AREAS, size=num_dev, replace=False).tolist()

                rows.append({
                    "review_id": self.state.next_id("REV"),
                    "employee_id": emp.employee_id,
                    "reviewer_id": emp.manager_id,
                    "cycle_id": cycle["cycle_id"],
                    "rating": rating,
                    "comments": f"Review for {cycle['name']}.",
                    "strengths": "; ".join(strengths),
                    "development_areas": "; ".join(dev_areas),
                })

        return rows

    def _generate_competency_assessments(
        self, rng: np.random.Generator, cycles: list[dict],
    ) -> list[dict]:
        """Generate skill/competency assessments linked to performance cycles."""
        rows = []

        # Only assess in annual cycles (H2)
        annual_cycles = [c for c in cycles if c["name"].startswith("H2")]

        for cycle in annual_cycles:
            active_emps = self.state.active_employees_at(cycle["end_date"])

            for emp in active_emps:
                if emp.hire_date > cycle["end_date"] - timedelta(days=90):
                    continue

                # Pick 2-4 relevant skills from the catalog
                relevant_skills = _get_relevant_skills(rng, emp.job_family)
                num_assess = min(len(relevant_skills), int(rng.integers(2, 5)))
                assessed_skills = rng.choice(relevant_skills, size=num_assess, replace=False)

                for skill in assessed_skills:
                    current = int(rng.integers(1, 5))
                    target = min(5, current + int(rng.integers(0, 3)))

                    rows.append({
                        "assessment_id": self.state.next_id("ASSESS"),
                        "employee_id": emp.employee_id,
                        "cycle_id": cycle["cycle_id"],
                        "skill_id": skill["id"],
                        "skill_name": skill["name"],
                        "current_level": current,
                        "target_level": target,
                    })

        return rows

    def validate(self) -> list[str]:
        errors = super().validate()

        reviews_df = self._dataframes.get("performance_reviews")
        if reviews_df is not None:
            # Ratings should be 1.0-5.0
            out_of_range = reviews_df[
                (reviews_df["rating"] < 1.0) | (reviews_df["rating"] > 5.0)
            ]
            if len(out_of_range) > 0:
                errors.append(f"{len(out_of_range)} reviews with ratings outside 1.0-5.0")

            # All employee_ids should exist
            emp_ids = {e.employee_id for e in self.state.employees.values()}
            review_emp_ids = set(reviews_df["employee_id"])
            orphans = review_emp_ids - emp_ids
            if orphans:
                errors.append(f"{len(orphans)} reviews reference non-existent employees")

        return errors


def _get_relevant_skills(rng: np.random.Generator, job_family: str) -> list[dict]:
    """Return skills relevant to a job family."""
    family_skills = {
        "JF-ENG": ["Technical", "Leadership"],
        "JF-DATA": ["Technical", "Data", "Leadership"],
        "JF-PROD": ["Product", "Leadership", "Business"],
        "JF-DESIGN": ["Design", "Product"],
        "JF-SALES": ["Business", "Leadership"],
        "JF-CS": ["Business", "Leadership"],
        "JF-MKTG": ["Business", "Data"],
        "JF-FIN": ["Business", "Data"],
        "JF-HR": ["Business", "Leadership"],
        "JF-LEGAL": ["Business"],
        "JF-OPS": ["Technical", "Business"],
        "JF-EXEC": ["Leadership", "Business"],
    }
    categories = family_skills.get(job_family, ["Business", "Leadership"])
    return [s for s in SKILL_CATALOG if s["category"] in categories]

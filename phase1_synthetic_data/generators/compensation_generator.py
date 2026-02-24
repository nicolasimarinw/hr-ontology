"""Compensation generator: salary bands, base salary, bonuses, equity grants."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from config.company_profile import COMPANY, JOB_FAMILIES, JOB_LEVELS
from phase1_synthetic_data.generators.base_generator import BaseGenerator
from phase1_synthetic_data.generators.distributions import (
    apply_pay_gap, lognormal_salary, random_date_between,
)
from phase1_synthetic_data.generators.shared_state import SharedState

# Salary band midpoints by level (USD)
LEVEL_MIDPOINTS = {
    "L1": 75_000,
    "L2": 95_000,
    "L3": 125_000,
    "L4": 160_000,
    "M1": 145_000,
    "M2": 170_000,
    "D1": 200_000,
    "D2": 235_000,
    "VP": 300_000,
    "CX": 400_000,
}

# Job family salary multipliers (some families pay more)
FAMILY_MULTIPLIERS = {
    "JF-ENG": 1.10,
    "JF-DATA": 1.08,
    "JF-PROD": 1.05,
    "JF-SALES": 1.00,  # base + commission
    "JF-DESIGN": 1.00,
    "JF-CS": 0.92,
    "JF-MKTG": 0.95,
    "JF-FIN": 1.00,
    "JF-HR": 0.93,
    "JF-LEGAL": 1.05,
    "JF-OPS": 0.95,
    "JF-EXEC": 1.15,
}

# Bonus target as % of base salary by level
BONUS_TARGETS = {
    "L1": 0.05, "L2": 0.08, "L3": 0.10, "L4": 0.12,
    "M1": 0.15, "M2": 0.18, "D1": 0.20, "D2": 0.25,
    "VP": 0.30, "CX": 0.50,
}

# Equity grant eligibility (levels that get equity)
EQUITY_ELIGIBLE_LEVELS = {"L4", "M1", "M2", "D1", "D2", "VP", "CX"}


class CompensationGenerator(BaseGenerator):
    name = "compensation"

    def generate(self) -> None:
        rng = self.state.rng

        # 1. Generate salary bands
        salary_bands = self._generate_salary_bands()

        # 2. Generate base salary records (with history)
        base_salaries = self._generate_base_salaries(rng)

        # 3. Generate bonus records
        bonuses = self._generate_bonuses(rng)

        # 4. Generate equity grants
        equity_grants = self._generate_equity_grants(rng)

        self.register("salary_bands", pd.DataFrame(salary_bands))
        self.register("base_salary", pd.DataFrame(base_salaries))
        self.register("bonuses", pd.DataFrame(bonuses))
        self.register("equity_grants", pd.DataFrame(equity_grants))

    def _generate_salary_bands(self) -> list[dict]:
        """Generate salary band definitions for each job family + level combination."""
        rows = []
        band_counter = 0

        for family in JOB_FAMILIES:
            multiplier = FAMILY_MULTIPLIERS.get(family["id"], 1.0)
            for level in JOB_LEVELS:
                midpoint = LEVEL_MIDPOINTS.get(level["id"], 100_000) * multiplier
                band_counter += 1
                rows.append({
                    "band_id": f"BAND-{band_counter:04d}",
                    "job_family": family["id"],
                    "job_family_name": family["name"],
                    "job_level": level["id"],
                    "job_level_name": level["name"],
                    "min_salary": round(midpoint * 0.80),
                    "midpoint": round(midpoint),
                    "max_salary": round(midpoint * 1.20),
                    "currency": "USD",
                })

        return rows

    def _generate_base_salaries(self, rng: np.random.Generator) -> list[dict]:
        """Generate base salary records for every employee, with history for tenured ones."""
        rows = []

        for emp in self.state.employees.values():
            midpoint = LEVEL_MIDPOINTS.get(emp.job_level, 100_000)
            family_mult = FAMILY_MULTIPLIERS.get(emp.job_family, 1.0)
            target_midpoint = midpoint * family_mult

            # Initial hire salary (slightly below midpoint typically)
            hire_salary = lognormal_salary(rng, target_midpoint * 0.95, sigma=0.10)[0]

            # Apply pay gap
            hire_salary = apply_pay_gap(rng, hire_salary, emp.gender, emp.ethnicity)
            hire_salary = round(hire_salary / 1000) * 1000  # Round to nearest $1k

            rows.append({
                "salary_id": self.state.next_id("SAL"),
                "employee_id": emp.employee_id,
                "amount": hire_salary,
                "currency": "USD",
                "effective_date": emp.hire_date,
                "reason": "Hire",
            })

            # Annual merit increases for each full year of employment
            current_salary = hire_salary
            end_date = emp.termination_date or COMPANY["data_end_date"]
            tenure_years = (end_date - emp.hire_date).days / 365.25

            for year in range(1, int(tenure_years) + 1):
                increase_date = emp.hire_date + timedelta(days=int(year * 365.25))
                if increase_date > end_date:
                    break

                # Merit increase: 2-6% depending on level and randomness
                merit_pct = rng.uniform(0.02, 0.06)
                current_salary = current_salary * (1 + merit_pct)
                current_salary = round(current_salary / 1000) * 1000

                # Occasional promotions get bigger bumps
                is_promo = rng.random() < 0.15
                reason = "Promotion" if is_promo else "Merit"
                if is_promo:
                    current_salary = current_salary * 1.10  # Extra 10% for promotion
                    current_salary = round(current_salary / 1000) * 1000

                rows.append({
                    "salary_id": self.state.next_id("SAL"),
                    "employee_id": emp.employee_id,
                    "amount": current_salary,
                    "currency": "USD",
                    "effective_date": increase_date,
                    "reason": reason,
                })

        return rows

    def _generate_bonuses(self, rng: np.random.Generator) -> list[dict]:
        """Generate annual and spot bonuses."""
        rows = []

        for emp in self.state.employees.values():
            target_pct = BONUS_TARGETS.get(emp.job_level, 0.05)
            end_date = emp.termination_date or COMPANY["data_end_date"]

            # Annual bonuses for each calendar year during employment
            for year in range(COMPANY["data_start_date"].year, end_date.year + 1):
                bonus_date = date(year, 3, 15)  # Q1 payout
                if bonus_date < emp.hire_date or bonus_date > end_date:
                    continue

                # Get the salary at that point (approximate with hire salary * years)
                years_in = max(1, (bonus_date - emp.hire_date).days / 365.25)
                approx_salary = LEVEL_MIDPOINTS.get(emp.job_level, 100_000)
                approx_salary *= FAMILY_MULTIPLIERS.get(emp.job_family, 1.0)

                # Actual payout varies from 0-150% of target
                actual_pct = target_pct * rng.uniform(0.5, 1.5)
                amount = round(approx_salary * actual_pct)

                rows.append({
                    "bonus_id": self.state.next_id("BON"),
                    "employee_id": emp.employee_id,
                    "type": "Annual",
                    "target_pct": round(target_pct, 3),
                    "actual_pct": round(actual_pct, 3),
                    "amount": amount,
                    "payout_date": bonus_date,
                })

            # Random spot bonuses (~10% chance per year)
            tenure_years = (end_date - emp.hire_date).days / 365.25
            if rng.random() < 0.10 * tenure_years:
                spot_date = random_date_between(rng, emp.hire_date, end_date)[0]
                spot_amount = rng.choice([1000, 2000, 2500, 5000, 10000])
                rows.append({
                    "bonus_id": self.state.next_id("BON"),
                    "employee_id": emp.employee_id,
                    "type": "Spot",
                    "target_pct": 0.0,
                    "actual_pct": 0.0,
                    "amount": spot_amount,
                    "payout_date": spot_date,
                })

        return rows

    def _generate_equity_grants(self, rng: np.random.Generator) -> list[dict]:
        """Generate equity/stock option grants for eligible levels."""
        rows = []

        for emp in self.state.employees.values():
            if emp.job_level not in EQUITY_ELIGIBLE_LEVELS:
                continue

            # Initial hire grant
            grant_shares = {
                "L4": 500, "M1": 750, "M2": 1000, "D1": 2000,
                "D2": 3000, "VP": 5000, "CX": 10000,
            }
            shares = grant_shares.get(emp.job_level, 500)
            # Add some variance
            shares = int(shares * rng.uniform(0.8, 1.3))

            rows.append({
                "grant_id": self.state.next_id("EQ"),
                "employee_id": emp.employee_id,
                "grant_date": emp.hire_date,
                "shares": shares,
                "vesting_schedule": "4-year with 1-year cliff",
                "exercise_price": round(rng.uniform(15.0, 45.0), 2),
            })

            # Refresh grants for tenured employees (annual, ~50% chance)
            end_date = emp.termination_date or COMPANY["data_end_date"]
            tenure_years = (end_date - emp.hire_date).days / 365.25

            for year in range(1, int(tenure_years) + 1):
                if rng.random() < 0.50:
                    refresh_date = emp.hire_date + timedelta(days=int(year * 365.25))
                    if refresh_date > end_date:
                        break
                    refresh_shares = int(shares * rng.uniform(0.2, 0.5))
                    rows.append({
                        "grant_id": self.state.next_id("EQ"),
                        "employee_id": emp.employee_id,
                        "grant_date": refresh_date,
                        "shares": refresh_shares,
                        "vesting_schedule": "4-year monthly",
                        "exercise_price": round(rng.uniform(20.0, 60.0), 2),
                    })

        return rows

    def validate(self) -> list[str]:
        errors = super().validate()

        base_df = self._dataframes.get("base_salary")
        if base_df is not None:
            # Every employee should have at least one salary record
            emp_ids = {e.employee_id for e in self.state.employees.values()}
            salary_emp_ids = set(base_df["employee_id"])
            missing = emp_ids - salary_emp_ids
            if missing:
                errors.append(f"{len(missing)} employees have no salary record")

            # No negative salaries
            neg = base_df[base_df["amount"] < 0]
            if len(neg) > 0:
                errors.append(f"{len(neg)} negative salary records found")

        return errors

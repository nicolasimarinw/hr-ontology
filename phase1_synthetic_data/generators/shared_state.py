"""Cross-system shared state for referential integrity across all generators."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np

from config.settings import RANDOM_SEED


@dataclass
class Employee:
    employee_id: str
    first_name: str
    last_name: str
    email: str
    hire_date: date
    birth_date: date
    gender: str
    ethnicity: str
    location_id: str
    department_id: str
    position_id: str
    manager_id: Optional[str]
    job_level: str
    job_family: str
    status: str = "Active"
    termination_date: Optional[date] = None
    termination_reason: Optional[str] = None


@dataclass
class Department:
    dept_id: str
    name: str
    division_id: str
    head_id: Optional[str] = None


@dataclass
class Position:
    position_id: str
    title: str
    job_family: str
    job_level: str
    department_id: str


class SharedState:
    """Singleton maintaining referential integrity across all generators.

    Every generator reads from and writes to this shared state so that
    foreign keys (employee_id, dept_id, position_id, etc.) remain consistent
    across all generated tables.
    """

    _instance: Optional[SharedState] = None

    def __new__(cls) -> SharedState:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self.rng = np.random.default_rng(RANDOM_SEED)

        # Core registries
        self.employees: dict[str, Employee] = {}
        self.departments: dict[str, Department] = {}
        self.positions: dict[str, Position] = {}

        # Org tree: manager_id -> list of direct report employee_ids
        self.org_tree: dict[str, list[str]] = {}

        # Skill catalog (populated from company_profile)
        self.skill_catalog: list[dict] = []

        # Counters for ID generation
        self._counters: dict[str, int] = {}

    @classmethod
    def reset(cls) -> SharedState:
        """Reset the singleton (useful for testing)."""
        cls._instance = None
        return cls()

    def next_id(self, prefix: str) -> str:
        """Generate the next sequential ID for a given prefix."""
        count = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = count
        return f"{prefix}-{count:05d}"

    def register_employee(self, emp: Employee) -> None:
        """Register an employee and update the org tree."""
        self.employees[emp.employee_id] = emp
        if emp.manager_id:
            self.org_tree.setdefault(emp.manager_id, []).append(emp.employee_id)

    def register_department(self, dept: Department) -> None:
        self.departments[dept.dept_id] = dept

    def register_position(self, pos: Position) -> None:
        self.positions[pos.position_id] = pos

    def active_employees(self) -> list[Employee]:
        """Return all currently active employees."""
        return [e for e in self.employees.values() if e.status == "Active"]

    def terminated_employees(self) -> list[Employee]:
        """Return all terminated employees."""
        return [e for e in self.employees.values() if e.status == "Terminated"]

    def employees_in_department(self, dept_id: str) -> list[Employee]:
        """Return all employees in a given department."""
        return [e for e in self.employees.values() if e.department_id == dept_id]

    def direct_reports(self, manager_id: str) -> list[str]:
        """Return employee IDs of direct reports for a manager."""
        return self.org_tree.get(manager_id, [])

    def employees_at_level(self, level: str) -> list[Employee]:
        """Return all employees at a specific job level."""
        return [e for e in self.employees.values() if e.job_level == level]

    def active_employees_at(self, target_date: date) -> list[Employee]:
        """Return employees who were active on a specific date."""
        result = []
        for emp in self.employees.values():
            if emp.hire_date <= target_date:
                if emp.termination_date is None or emp.termination_date > target_date:
                    result.append(emp)
        return result

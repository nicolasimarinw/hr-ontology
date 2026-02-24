"""Time-series and temporal event generation helpers."""

from datetime import date, timedelta
from typing import Optional

import numpy as np


def generate_event_timeline(
    rng: np.random.Generator,
    hire_date: date,
    end_date: date,
    event_types: list[str],
    avg_events_per_year: float = 0.3,
    min_gap_days: int = 90,
) -> list[dict]:
    """Generate a sequence of temporal events for an employee.

    Returns list of {"event_type": str, "date": date} dicts, sorted by date.
    Events are spaced at least min_gap_days apart.
    """
    tenure_days = (end_date - hire_date).days
    if tenure_days < min_gap_days:
        return []

    tenure_years = tenure_days / 365.25
    expected_events = int(tenure_years * avg_events_per_year)
    num_events = rng.poisson(max(expected_events, 0))

    if num_events == 0:
        return []

    events = []
    current_date = hire_date + timedelta(days=min_gap_days)

    for _ in range(num_events):
        if current_date >= end_date:
            break

        remaining_days = (end_date - current_date).days
        if remaining_days < min_gap_days:
            break

        offset = rng.integers(min_gap_days, max(remaining_days, min_gap_days + 1))
        event_date = current_date + timedelta(days=int(offset))

        if event_date >= end_date:
            break

        event_type = rng.choice(event_types)
        events.append({"event_type": event_type, "date": event_date})
        current_date = event_date + timedelta(days=min_gap_days)

    return sorted(events, key=lambda e: e["date"])


def generate_review_dates(
    start_date: date,
    end_date: date,
    frequency: str = "semi-annual",
) -> list[date]:
    """Generate performance review cycle dates.

    frequency: "annual" (December) or "semi-annual" (June + December).
    """
    dates = []
    year = start_date.year

    while year <= end_date.year:
        if frequency in ("semi-annual", "semi_annual"):
            mid_year = date(year, 6, 30)
            if start_date <= mid_year <= end_date:
                dates.append(mid_year)

        year_end = date(year, 12, 15)
        if start_date <= year_end <= end_date:
            dates.append(year_end)

        year += 1

    return dates


def quarterly_dates(start_date: date, end_date: date) -> list[date]:
    """Generate quarterly dates (end of Q1-Q4) between start and end."""
    quarters = [(3, 31), (6, 30), (9, 30), (12, 31)]
    dates = []
    year = start_date.year

    while year <= end_date.year:
        for month, day in quarters:
            q_date = date(year, month, day)
            if start_date <= q_date <= end_date:
                dates.append(q_date)
        year += 1

    return dates


def workdays_between(start: date, end: date) -> int:
    """Count business days between two dates."""
    if start >= end:
        return 0

    days = 0
    current = start
    while current < end:
        if current.weekday() < 5:  # Mon-Fri
            days += 1
        current += timedelta(days=1)

    return days


def add_business_days(start: date, num_days: int) -> date:
    """Add business days to a date."""
    current = start
    added = 0
    while added < num_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current

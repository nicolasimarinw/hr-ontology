"""Statistical distribution helpers for realistic synthetic data generation."""

from datetime import date, timedelta
from typing import Optional

import numpy as np


def weighted_choice(rng: np.random.Generator, options: dict[str, float], size: int = 1) -> list[str]:
    """Pick from weighted options. options = {"Male": 0.58, "Female": 0.38, ...}"""
    keys = list(options.keys())
    weights = np.array(list(options.values()))
    weights = weights / weights.sum()  # normalize
    indices = rng.choice(len(keys), size=size, p=weights)
    return [keys[i] for i in indices]


def normal_clipped(rng: np.random.Generator, mean: float, std: float,
                   low: float, high: float, size: int = 1) -> np.ndarray:
    """Normal distribution clipped to [low, high]."""
    values = rng.normal(mean, std, size=size)
    return np.clip(values, low, high)


def lognormal_salary(rng: np.random.Generator, median: float, sigma: float = 0.15,
                     size: int = 1) -> np.ndarray:
    """Log-normal salary distribution centered around a median."""
    mu = np.log(median)
    return rng.lognormal(mu, sigma, size=size)


def beta_rating(rng: np.random.Generator, alpha: float = 5.0, beta: float = 2.0,
                low: float = 1.0, high: float = 5.0, size: int = 1) -> np.ndarray:
    """Beta distribution scaled to a rating range (default 1-5, right-skewed)."""
    raw = rng.beta(alpha, beta, size=size)
    return raw * (high - low) + low


def exponential_tenure(rng: np.random.Generator, scale: float = 3.3,
                       max_years: float = 15.0, size: int = 1) -> np.ndarray:
    """Exponential tenure distribution in years (median ~2.3 years with scale=3.3)."""
    values = rng.exponential(scale, size=size)
    return np.clip(values, 0.1, max_years)


def random_date_between(rng: np.random.Generator, start: date, end: date,
                        size: int = 1) -> list[date]:
    """Generate random dates uniformly between start and end."""
    delta_days = (end - start).days
    if delta_days <= 0:
        return [start] * size
    offsets = rng.integers(0, delta_days, size=size)
    return [start + timedelta(days=int(d)) for d in offsets]


def birth_date_from_age(rng: np.random.Generator, reference_date: date,
                        mean_age: float = 35.0, std_age: float = 9.0,
                        min_age: float = 22.0, max_age: float = 65.0,
                        size: int = 1) -> list[date]:
    """Generate birth dates based on age distribution at a reference date."""
    ages = normal_clipped(rng, mean_age, std_age, min_age, max_age, size=size)
    return [reference_date - timedelta(days=int(a * 365.25)) for a in ages]


def apply_pay_gap(
    rng: np.random.Generator,
    base_amount: float,
    gender: str,
    ethnicity: str,
    gap_config: Optional[dict] = None,
) -> float:
    """Apply subtle, realistic pay gaps based on gender and ethnicity.

    These are intentionally embedded so the ontology analytics can discover them.
    Default gaps approximate real-world US tech industry data.
    """
    if gap_config is None:
        gap_config = {
            "gender": {
                "Female": -0.06,       # ~6% gap
                "Non-binary": -0.04,   # ~4% gap
                "Male": 0.0,
            },
            "ethnicity": {
                "Black/African American": -0.05,
                "Hispanic/Latino": -0.04,
                "Two or More Races": -0.02,
                "Other": -0.02,
                "Asian": 0.0,
                "White": 0.0,
            },
        }

    gender_adjustment = gap_config["gender"].get(gender, 0.0)
    ethnicity_adjustment = gap_config["ethnicity"].get(ethnicity, 0.0)

    # Add noise so gaps aren't perfectly uniform (harder to detect, more realistic)
    noise = rng.normal(0, 0.02)
    total_adjustment = 1.0 + gender_adjustment + ethnicity_adjustment + noise

    return base_amount * total_adjustment

"""
Feature #6: Diffusion and Adoption Curves

Generates adoption timestamps following Rogers diffusion curve (S-curve/logistic).
Models how innovations spread through populations over time.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict


def generate_diffusion_timestamps(
    n_rows: int,
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
    curve_type: str = "logistic",
    inflection_point: float = 0.5,
    steepness: float = 10.0,
    rng: np.random.Generator = None
) -> pd.Series:
    """
    Generate adoption timestamps following a diffusion curve.

    Args:
        n_rows: Number of timestamps to generate
        start_time: Start of adoption period
        end_time: End of adoption period
        curve_type: "logistic" (S-curve), "exponential", or "linear"
        inflection_point: Point of maximum adoption rate (0-1, default 0.5)
        steepness: How steep the S-curve is (higher = steeper)
        rng: Random number generator

    Returns:
        Series of timestamps following the diffusion curve
    """
    if rng is None:
        rng = np.random.default_rng()

    # Generate uniform random values [0, 1]
    uniform_values = rng.random(n_rows)

    # Transform through inverse CDF of diffusion curve
    if curve_type == "logistic":
        # Logistic/S-curve: slow start, rapid middle, slow end
        # CDF: 1 / (1 + exp(-k*(x - inflection)))
        # Inverse: inflection + (1/k) * log(p / (1 - p))

        # Avoid edge cases
        uniform_values = np.clip(uniform_values, 0.0001, 0.9999)

        # Inverse logistic CDF
        normalized_times = inflection_point + (1.0 / steepness) * np.log(
            uniform_values / (1 - uniform_values)
        )

        # Clip to [0, 1] range
        normalized_times = np.clip(normalized_times, 0, 1)

    elif curve_type == "exponential":
        # Exponential growth: fast early adoption, slowing down
        # CDF: 1 - exp(-lambda * x)
        # Inverse: -log(1 - p) / lambda

        lambda_param = steepness
        normalized_times = -np.log(1 - uniform_values) / lambda_param
        normalized_times = np.clip(normalized_times, 0, 1)

    elif curve_type == "linear":
        # Linear: constant adoption rate
        normalized_times = uniform_values

    else:
        raise ValueError(f"Unknown curve_type: {curve_type}")

    # Convert normalized times [0, 1] to actual timestamps
    duration = (end_time - start_time).total_seconds()
    timestamps = [
        start_time + pd.Timedelta(seconds=duration * t)
        for t in normalized_times
    ]

    return pd.Series(timestamps)


def assign_adopter_categories(
    n_rows: int,
    distribution: Optional[Dict[str, float]] = None,
    rng: np.random.Generator = None
) -> pd.Series:
    """
    Assign Rogers adopter categories to entities.

    Args:
        n_rows: Number of entities
        distribution: Custom distribution dict or None for Rogers defaults
        rng: Random number generator

    Returns:
        Series of adopter categories
    """
    if rng is None:
        rng = np.random.default_rng()

    # Rogers diffusion of innovations model (default)
    if distribution is None:
        distribution = {
            "innovators": 0.025,
            "early_adopters": 0.135,
            "early_majority": 0.34,
            "late_majority": 0.34,
            "laggards": 0.16
        }

    categories = list(distribution.keys())
    weights = list(distribution.values())

    # Normalize weights
    total = sum(weights)
    weights = [w / total for w in weights]

    # Assign categories
    assignments = rng.choice(categories, size=n_rows, p=weights)

    return pd.Series(assignments)


def generate_viral_adoption(
    seed_adopters: int,
    viral_coefficient: float,
    population_size: int,
    timesteps: int,
    rng: np.random.Generator = None
) -> np.ndarray:
    """
    Simulate viral adoption dynamics.

    Args:
        seed_adopters: Initial number of adopters
        viral_coefficient: Average new adopters per existing adopter per timestep
        population_size: Total population size
        timesteps: Number of time steps to simulate
        rng: Random number generator

    Returns:
        Array of cumulative adopters at each timestep
    """
    if rng is None:
        rng = np.random.default_rng()

    adopters = [seed_adopters]

    for t in range(1, timesteps):
        current_adopters = adopters[-1]

        if current_adopters >= population_size:
            adopters.append(population_size)
            continue

        # Viral growth: new adopters = current * viral_coefficient * (1 - saturation)
        saturation = current_adopters / population_size
        expected_new = current_adopters * viral_coefficient * (1 - saturation)

        # Add Poisson noise
        new_adopters = rng.poisson(expected_new)

        # Cap at population size
        total = min(current_adopters + new_adopters, population_size)
        adopters.append(total)

    return np.array(adopters)

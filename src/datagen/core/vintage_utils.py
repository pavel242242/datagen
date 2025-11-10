"""Utilities for vintage effects (Feature #1: Entity Vintage Effects).

Provides helpers for calculating entity age and evaluating age-based curves.
"""

import numpy as np
import pandas as pd
from typing import Union, List
import logging

logger = logging.getLogger(__name__)


def calculate_entity_ages(
    entity_created_at: pd.Series, reference_time: pd.Series, time_unit: str = "day"
) -> np.ndarray:
    """
    Calculate entity ages in specified time units.

    Args:
        entity_created_at: Timestamp when each entity was created
        reference_time: Reference timestamp (e.g., fact timestamp)
        time_unit: Unit for age calculation ("day", "month", "year")

    Returns:
        Array of ages in specified time units

    Examples:
        >>> entity_created = pd.to_datetime(["2024-01-01", "2024-02-01"])
        >>> fact_time = pd.to_datetime(["2024-03-01", "2024-04-01"])
        >>> calculate_entity_ages(entity_created, fact_time, "month")
        array([2, 2])  # 2 months old, 2 months old
    """
    # Normalize timezones - convert both to tz-naive to avoid mismatch errors
    # Handle both Series (with .dt accessor) and DatetimeIndex
    if hasattr(entity_created_at, "dt") and entity_created_at.dt.tz is not None:
        entity_created_at = entity_created_at.dt.tz_localize(None)
    elif hasattr(entity_created_at, "tz") and entity_created_at.tz is not None:
        entity_created_at = entity_created_at.tz_localize(None)

    if hasattr(reference_time, "dt") and reference_time.dt.tz is not None:
        reference_time = reference_time.dt.tz_localize(None)
    elif hasattr(reference_time, "tz") and reference_time.tz is not None:
        reference_time = reference_time.tz_localize(None)

    # Calculate age in days first
    # When subtracting DatetimeIndex, we get TimedeltaIndex, not Series
    timedelta = reference_time - entity_created_at
    age_days = timedelta.days.values if hasattr(timedelta, "days") else timedelta.dt.days.values

    # Ensure non-negative ages (entities can't be used before they're created)
    age_days = np.maximum(0, age_days)

    # Convert to requested time unit
    if time_unit == "day":
        return age_days
    elif time_unit == "month":
        return age_days / 30.0  # Approximate month as 30 days
    elif time_unit == "year":
        return age_days / 365.0  # Approximate year as 365 days
    else:
        raise ValueError(f"Unknown time_unit: {time_unit}. Expected 'day', 'month', or 'year'")


def evaluate_curve(ages: np.ndarray, curve_spec: Union[List[float], dict]) -> np.ndarray:
    """
    Evaluate a curve (array-based or parametric) at given ages.

    Supports two curve types:
    1. **Array-based**: List of multipliers for discrete age bins
       - Example: [1.0, 0.75, 0.6, 0.5] for ages 0, 1, 2, 3+

    2. **Parametric**: Dictionary with curve_type and params
       - logarithmic: multiplier = a + b * log(age + 1)
       - exponential: multiplier = a * exp(b * age)
       - linear: multiplier = a + b * age

    Args:
        ages: Array of entity ages in time units
        curve_spec: Either a list of floats (array-based) or dict (parametric)

    Returns:
        Array of multipliers corresponding to each age

    Examples:
        >>> ages = np.array([0, 1, 2, 5])
        >>> evaluate_curve(ages, [1.0, 0.75, 0.6, 0.5])
        array([1.0, 0.75, 0.6, 0.5])

        >>> evaluate_curve(ages, {"curve_type": "logarithmic", "params": {"a": 1.0, "b": -0.15}})
        array([1.0, 0.896, 0.835, 0.731])
    """
    if isinstance(curve_spec, list):
        return _evaluate_array_curve(ages, curve_spec)
    elif isinstance(curve_spec, dict):
        return _evaluate_parametric_curve(ages, curve_spec)
    else:
        raise ValueError(f"Invalid curve_spec type: {type(curve_spec)}. Expected list or dict")


def _evaluate_array_curve(ages: np.ndarray, curve: List[float]) -> np.ndarray:
    """
    Evaluate array-based curve.

    Maps ages to discrete bins:
    - Age 0 → curve[0]
    - Age 1 → curve[1]
    - Age N → curve[min(N, len(curve)-1)]  # Last value for ages beyond array

    Args:
        ages: Array of entity ages (can be floats)
        curve: List of multipliers

    Returns:
        Array of multipliers
    """
    if not curve:
        raise ValueError("Array curve cannot be empty")

    # Round ages to nearest integer for binning
    age_bins = np.round(ages).astype(int)

    # Clamp to valid indices (0 to len(curve)-1)
    age_bins = np.clip(age_bins, 0, len(curve) - 1)

    # Lookup multipliers
    multipliers = np.array([curve[idx] for idx in age_bins])

    return multipliers


def _evaluate_parametric_curve(ages: np.ndarray, spec: dict) -> np.ndarray:
    """
    Evaluate parametric curve.

    Supported curve types:
    - logarithmic: multiplier = a + b * log(age + 1)
    - exponential: multiplier = a * exp(b * age)
    - linear: multiplier = a + b * age

    Args:
        ages: Array of entity ages
        spec: Dict with 'curve_type' and 'params' (containing 'a' and 'b')

    Returns:
        Array of multipliers
    """
    curve_type = spec.get("curve_type")
    params = spec.get("params", {})

    if not curve_type:
        raise ValueError("Parametric curve must have 'curve_type'")
    if not params:
        raise ValueError("Parametric curve must have 'params'")

    a = params.get("a")
    b = params.get("b")

    if a is None or b is None:
        raise ValueError("Parametric curve params must include 'a' and 'b'")

    if curve_type == "logarithmic":
        # multiplier = a + b * log(age + 1)
        # Adding 1 to avoid log(0)
        multipliers = a + b * np.log(ages + 1)

    elif curve_type == "exponential":
        # multiplier = a * exp(b * age)
        multipliers = a * np.exp(b * ages)

    elif curve_type == "linear":
        # multiplier = a + b * age
        multipliers = a + b * ages

    else:
        raise ValueError(
            f"Unknown curve_type: {curve_type}. "
            f"Expected 'logarithmic', 'exponential', or 'linear'"
        )

    # Ensure multipliers are non-negative (activity/value can't be negative)
    multipliers = np.maximum(0, multipliers)

    return multipliers


def apply_vintage_multipliers_to_fanout(
    fanout_counts: np.ndarray, entity_ages: np.ndarray, vintage_config: dict
) -> np.ndarray:
    """
    Apply age-based multipliers to fanout counts.

    Looks for "activity_decay" or similar configurations in vintage_config
    and applies the corresponding curve to modify fanout counts.

    Args:
        fanout_counts: Original fanout counts for each entity
        entity_ages: Age of each entity in time units
        vintage_config: vintage_behavior configuration from schema

    Returns:
        Modified fanout counts with vintage multipliers applied
    """
    if not vintage_config:
        return fanout_counts

    age_based_multipliers = vintage_config.get("age_based_multipliers", {})

    # Look for fanout-applicable multipliers
    result_counts = fanout_counts.copy().astype(float)

    for multiplier_name, multiplier_spec in age_based_multipliers.items():
        applies_to = multiplier_spec.get("applies_to")

        # Check if this multiplier applies to fanout
        if applies_to == "fanout":
            curve = multiplier_spec.get("curve")
            if not curve:
                logger.warning(
                    f"Multiplier '{multiplier_name}' has applies_to='fanout' but no curve defined"
                )
                continue

            # Evaluate curve at entity ages
            multipliers = evaluate_curve(entity_ages, curve)

            # Apply multipliers
            result_counts *= multipliers

            logger.debug(
                f"  Applied vintage multiplier '{multiplier_name}' to fanout: "
                f"mean changed from {fanout_counts.mean():.2f} to {result_counts.mean():.2f}"
            )

    # Round and convert to int, ensuring non-negative
    return np.maximum(0, np.round(result_counts)).astype(int)


def apply_vintage_multipliers_to_values(
    values: np.ndarray, entity_ages: np.ndarray, column_name: str, vintage_config: dict
) -> np.ndarray:
    """
    Apply age-based multipliers to column values.

    Looks for multipliers that apply to the specified column name
    and applies the corresponding curve.

    Args:
        values: Original column values
        entity_ages: Age of entity for each value
        column_name: Name of the column being modified
        vintage_config: vintage_behavior configuration from schema

    Returns:
        Modified values with vintage multipliers applied
    """
    if not vintage_config:
        return values

    age_based_multipliers = vintage_config.get("age_based_multipliers", {})

    result_values = values.copy().astype(float)

    for multiplier_name, multiplier_spec in age_based_multipliers.items():
        applies_to = multiplier_spec.get("applies_to")

        # Check if this multiplier applies to this column
        # applies_to can be:
        # - "fanout" (skip for values)
        # - "all" (apply to all columns)
        # - ["column1", "column2"] (list of column names)
        # - "column1" (single column name)

        if applies_to == "fanout":
            continue  # Skip fanout multipliers for column values

        should_apply = False
        if applies_to == "all":
            should_apply = True
        elif isinstance(applies_to, list) and column_name in applies_to:
            should_apply = True
        elif isinstance(applies_to, str) and applies_to == column_name:
            should_apply = True

        if should_apply:
            curve = multiplier_spec.get("curve")
            if not curve:
                logger.warning(
                    f"Multiplier '{multiplier_name}' applies to '{column_name}' but no curve defined"
                )
                continue

            # Evaluate curve at entity ages
            multipliers = evaluate_curve(entity_ages, curve)

            # Apply multipliers
            result_values *= multipliers

            logger.debug(
                f"  Applied vintage multiplier '{multiplier_name}' to column '{column_name}': "
                f"mean changed from {values.mean():.2f} to {result_values.mean():.2f}"
            )

    return result_values

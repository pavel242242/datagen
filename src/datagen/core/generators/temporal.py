"""Temporal generators: datetime_series, seasonality patterns."""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Datetime Series Generator
# ============================================================================

def generate_datetime_series(
    start: str,
    end: str,
    freq: str,
    size: int,
    rng: np.random.Generator,
    pattern: Optional[dict] = None,
    patterns: Optional[list] = None
) -> pd.Series:
    """
    Generate datetime series with optional seasonality pattern(s).

    Args:
        start: ISO8601 start datetime
        end: ISO8601 end datetime
        freq: Pandas frequency string (H, D, M, etc.)
        size: Number of datetimes to generate
        rng: Random number generator
        pattern: Optional single pattern {"dimension": "hour|dow|month", "weights": [floats]}
        patterns: Optional list of patterns for composite effects

    Returns:
        Pandas Series of datetimes

    Examples:
        >>> rng = np.random.default_rng(42)
        >>> series = generate_datetime_series(
        ...     "2024-01-01T00:00:00Z", "2024-03-31T23:59:59Z", "D", 10, rng
        ... )
        >>> len(series)
        10
    """
    # Parse datetimes
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)

    # Create full range
    date_range = pd.date_range(start_dt, end_dt, freq=freq)

    if len(date_range) == 0:
        raise ValueError(f"No datetimes in range {start} to {end} with freq {freq}")

    # Apply pattern weights if provided
    weights = None

    if patterns:
        # Composite patterns: multiply weights from all dimensions
        weights = np.ones(len(date_range))
        for ptn in patterns:
            ptn_weights = apply_temporal_pattern(date_range, ptn)
            # Denormalize pattern weights (multiply by count to get raw weights)
            raw_weights = ptn_weights * len(date_range)
            # Multiply into composite weights
            weights *= raw_weights
        # Normalize final weights
        weights = weights / weights.sum()
    elif pattern:
        # Single pattern
        weights = apply_temporal_pattern(date_range, pattern)

    # Sample
    indices = rng.choice(len(date_range), size=size, p=weights)
    return pd.Series(date_range[indices]).reset_index(drop=True)


def apply_temporal_pattern(
    date_range: pd.DatetimeIndex,
    pattern: dict
) -> np.ndarray:
    """
    Apply temporal pattern weights to date range.

    Args:
        date_range: DatetimeIndex
        pattern: {"dimension": "hour|dow|month", "weights": [floats]}

    Returns:
        Normalized probability weights for each timestamp
    """
    dimension = pattern["dimension"]
    weights_list = pattern["weights"]

    # Extract temporal component
    if dimension == "hour":
        # Hour of day (0-23)
        components = date_range.hour
        expected_len = 24
    elif dimension == "dow":
        # Day of week (0=Monday, 6=Sunday)
        components = date_range.dayofweek
        expected_len = 7
    elif dimension == "month":
        # Month (1-12) -> convert to 0-11
        components = date_range.month - 1
        expected_len = 12
    else:
        raise ValueError(f"Unknown pattern dimension: {dimension}")

    if len(weights_list) != expected_len:
        raise ValueError(
            f"Pattern dimension {dimension} requires {expected_len} weights, "
            f"got {len(weights_list)}"
        )

    # Map weights to each timestamp
    weights_array = np.array(weights_list, dtype=float)
    timestamp_weights = weights_array[components]

    # Normalize
    total = timestamp_weights.sum()
    if total == 0:
        raise ValueError("Pattern weights sum to zero")

    return timestamp_weights / total


def get_seasonality_multiplier(
    timestamps: Union[pd.Series, np.ndarray],
    dimension: str,
    weights: list[float]
) -> np.ndarray:
    """
    Get seasonality multipliers for timestamps.

    Used by modifiers to scale numeric values based on time.

    Args:
        timestamps: Array of timestamps
        dimension: "hour", "dow", or "month"
        weights: Multipliers for each time component (mean should be ~1.0)

    Returns:
        Array of multipliers

    Examples:
        >>> ts = pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03'])
        >>> # Monday=1.0, Tuesday=1.2, Wednesday=0.9
        >>> mults = get_seasonality_multiplier(ts, "dow", [1.0, 1.2, 0.9, 1.0, 1.0, 1.0, 1.0])
        >>> len(mults)
        3
    """
    ts = pd.to_datetime(timestamps)

    # Handle both Series (needs .dt accessor) and DatetimeIndex (direct access)
    if isinstance(ts, pd.Series):
        dt_accessor = ts.dt
    else:
        dt_accessor = ts

    if dimension == "hour":
        components = dt_accessor.hour
        expected_len = 24
    elif dimension == "dow":
        components = dt_accessor.dayofweek
        expected_len = 7
    elif dimension == "month":
        components = dt_accessor.month - 1
        expected_len = 12
    else:
        raise ValueError(f"Unknown seasonality dimension: {dimension}")

    if len(weights) != expected_len:
        raise ValueError(
            f"Seasonality dimension {dimension} requires {expected_len} weights, "
            f"got {len(weights)}"
        )

    weights_array = np.array(weights, dtype=float)
    return weights_array[components.values]

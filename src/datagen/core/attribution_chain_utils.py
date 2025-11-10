"""
Feature #5: Multi-Touch Attribution Chains

Generates attribution touchpoint chains for conversion events.
Supports multiple attribution models: linear, first_touch, last_touch, time_decay.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List


def generate_attribution_chains(
    conversion_df: pd.DataFrame,
    conversion_id_col: str,
    conversion_time_col: str,
    touchpoint_channels: List[str],
    min_touches: int,
    max_touches: int,
    time_window_days: int,
    attribution_model: str = "linear",
    time_decay_halflife_days: Optional[float] = None,
    rng: np.random.Generator = None
) -> pd.DataFrame:
    """
    Generate multi-touch attribution chains for conversion events.

    Args:
        conversion_df: DataFrame of conversion events
        conversion_id_col: Name of conversion ID column
        conversion_time_col: Name of conversion timestamp column
        touchpoint_channels: List of possible touchpoint channels
        min_touches: Minimum touchpoints per conversion
        max_touches: Maximum touchpoints per conversion
        time_window_days: Days before conversion to generate touchpoints
        attribution_model: "linear", "first_touch", "last_touch", "time_decay"
        time_decay_halflife_days: Half-life for time decay model
        rng: Random number generator

    Returns:
        DataFrame with columns: touchpoint_id, conversion_id, channel,
                                timestamp, position, attribution_weight
    """
    if rng is None:
        rng = np.random.default_rng()

    touchpoints = []
    touchpoint_id = 1

    for _, conversion in conversion_df.iterrows():
        conversion_id = conversion[conversion_id_col]
        conversion_time = pd.Timestamp(conversion[conversion_time_col])

        # Determine number of touchpoints for this conversion
        n_touches = rng.integers(min_touches, max_touches + 1)

        # Generate touchpoint timestamps (spread over time window)
        # Use exponential distribution to cluster more touchpoints near conversion
        days_before = rng.exponential(time_window_days / 3, size=n_touches)
        days_before = np.clip(days_before, 0, time_window_days)
        days_before = np.sort(days_before)[::-1]  # Oldest first

        touchpoint_times = [
            conversion_time - pd.Timedelta(days=float(days))
            for days in days_before
        ]

        # Select channels for each touchpoint
        touchpoint_channel_list = rng.choice(
            touchpoint_channels,
            size=n_touches,
            replace=True
        )

        # Calculate attribution weights
        weights = calculate_attribution_weights(
            n_touches=n_touches,
            model=attribution_model,
            days_before=days_before,
            halflife_days=time_decay_halflife_days or time_window_days / 2
        )

        # Create touchpoint records
        for i, (channel, timestamp, weight) in enumerate(zip(
            touchpoint_channel_list, touchpoint_times, weights
        )):
            touchpoints.append({
                "touchpoint_id": touchpoint_id,
                "conversion_id": conversion_id,
                "channel": channel,
                "timestamp": timestamp,
                "position": i + 1,  # 1-indexed position
                "attribution_weight": weight
            })
            touchpoint_id += 1

    return pd.DataFrame(touchpoints)


def calculate_attribution_weights(
    n_touches: int,
    model: str,
    days_before: np.ndarray,
    halflife_days: float
) -> np.ndarray:
    """
    Calculate attribution weights based on model.

    Args:
        n_touches: Number of touchpoints
        model: "linear", "first_touch", "last_touch", "time_decay"
        days_before: Days before conversion for each touchpoint
        halflife_days: Half-life for time decay model

    Returns:
        Array of attribution weights (sum to 1.0)
    """
    if model == "linear":
        # Equal credit to all touchpoints
        weights = np.ones(n_touches) / n_touches

    elif model == "first_touch":
        # 100% credit to first touchpoint
        weights = np.zeros(n_touches)
        weights[0] = 1.0

    elif model == "last_touch":
        # 100% credit to last touchpoint
        weights = np.zeros(n_touches)
        weights[-1] = 1.0

    elif model == "time_decay":
        # Exponential decay: closer touchpoints get more credit
        # Use days_before (inverted so closer = higher weight)
        max_days = days_before[0] if len(days_before) > 0 else 1.0
        time_to_conversion = max_days - days_before

        # Exponential decay formula: weight = 2^(-days_before / halflife)
        weights = np.power(2.0, -days_before / halflife_days)

        # Normalize to sum to 1
        weights = weights / weights.sum()

    else:
        raise ValueError(f"Unknown attribution model: {model}")

    return weights


def validate_attribution_chain(
    touchpoints_df: pd.DataFrame,
    conversions_df: pd.DataFrame,
    conversion_id_col: str
) -> Dict[str, any]:
    """
    Validate attribution chain data quality.

    Returns:
        Dictionary with validation results
    """
    results = {
        "total_conversions": len(conversions_df),
        "total_touchpoints": len(touchpoints_df),
        "avg_touchpoints_per_conversion": len(touchpoints_df) / len(conversions_df) if len(conversions_df) > 0 else 0,
        "issues": []
    }

    # Check that all conversion IDs in touchpoints exist in conversions
    touchpoint_conversion_ids = set(touchpoints_df["conversion_id"].unique())
    conversion_ids = set(conversions_df[conversion_id_col].unique())

    orphaned = touchpoint_conversion_ids - conversion_ids
    if orphaned:
        results["issues"].append(f"Found {len(orphaned)} orphaned touchpoints (no matching conversion)")

    # Check attribution weights sum to 1.0 per conversion
    weight_sums = touchpoints_df.groupby("conversion_id")["attribution_weight"].sum()
    invalid_sums = weight_sums[(weight_sums < 0.99) | (weight_sums > 1.01)]
    if len(invalid_sums) > 0:
        results["issues"].append(f"Found {len(invalid_sums)} conversions with attribution weights not summing to 1.0")

    # Check temporal ordering: all touchpoints should be before conversion
    merged = touchpoints_df.merge(
        conversions_df[[conversion_id_col, "timestamp"]],
        left_on="conversion_id",
        right_on=conversion_id_col,
        suffixes=("_touch", "_conv")
    )

    violations = merged[merged["timestamp_touch"] > merged["timestamp_conv"]]
    if len(violations) > 0:
        results["issues"].append(f"Found {len(violations)} touchpoints after conversion time")

    results["valid"] = len(results["issues"]) == 0

    return results

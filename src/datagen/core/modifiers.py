"""Modifier functions for transforming generated values."""

import numpy as np
import pandas as pd
from typing import Any, Optional
import logging

from datagen.core.generators.temporal import get_seasonality_multiplier

logger = logging.getLogger(__name__)


def apply_modifiers(
    values: np.ndarray,
    modifiers: list,
    rng: np.random.Generator,
    context: Optional[pd.DataFrame] = None
) -> np.ndarray:
    """
    Apply a sequence of modifiers to values.

    Args:
        values: Input values
        modifiers: List of modifier specs (Pydantic models or dicts)
        rng: Random generator
        context: Optional DataFrame context for time-based modifiers

    Returns:
        Modified values
    """
    result = values.copy()

    for modifier in modifiers:
        # Handle both Pydantic models and dicts
        if hasattr(modifier, 'transform'):
            transform = modifier.transform
            args = modifier.args
        else:
            transform = modifier["transform"]
            args = modifier["args"]

        if transform == "multiply":
            result = modify_multiply(result, args["factor"])

        elif transform == "add":
            result = modify_add(result, args["value"])

        elif transform == "clamp":
            result = modify_clamp(result, args["min"], args["max"])

        elif transform == "jitter":
            result = modify_jitter(result, rng, args["std"], args.get("mode", "add"))

        elif transform == "map_values":
            result = modify_map_values(result, args["mapping"])

        elif transform == "seasonality":
            # For seasonality on datetime columns, use the values being modified as timestamps
            # For seasonality on numeric columns, need a timestamp column in context
            if pd.api.types.is_datetime64_any_dtype(result):
                # Modifying a datetime column - this is selecting timestamps
                # Seasonality doesn't make sense here, should be used on numeric values
                logger.warning("Seasonality modifier on datetime column doesn't make sense, skipping")
            elif context is None:
                logger.warning("Seasonality modifier requires context, skipping")
            else:
                # Find timestamp column in context to get seasonality multipliers
                timestamp_col = None
                for col in context.columns:
                    if pd.api.types.is_datetime64_any_dtype(context[col]):
                        timestamp_col = col
                        break

                if timestamp_col is None:
                    logger.warning("Seasonality modifier requires datetime column in context, skipping")
                else:
                    result = modify_seasonality(
                        result,
                        context[timestamp_col],
                        args["dimension"],
                        args["weights"]
                    )

        elif transform == "time_jitter":
            result = modify_time_jitter(result, rng, args["std_minutes"])

        elif transform == "effect":
            # Effects require external table data
            if context is None:
                logger.warning("Effect modifier requires context, skipping")
            else:
                # Get effect table from context (passed by executor)
                effect_table_name = args.get("effect_table")
                if f"_effect_{effect_table_name}" not in context.columns:
                    logger.warning(f"Effect table {effect_table_name} not in context, skipping")
                else:
                    result = modify_effect(
                        result,
                        context,
                        args["effect_table"],
                        args["on"],
                        args["window"],
                        args["map"]
                    )

        elif transform == "outliers":
            result = modify_outliers(
                result,
                rng,
                args["rate"],
                args["mode"],
                args.get("magnitude_dist", {"type": "lognormal", "params": {"mean": 0, "sigma": 0.5}})
            )

        elif transform == "trend":
            if context is None:
                logger.warning("Trend modifier requires context, skipping")
            else:
                # Get timestamp column reference
                time_col = args.get("time_reference")
                if time_col not in context.columns:
                    logger.warning(f"Trend modifier time_reference '{time_col}' not found in context, skipping")
                else:
                    result = modify_trend(
                        result,
                        context[time_col],
                        args["type"],
                        args.get("growth_rate"),
                        args.get("params", {})
                    )

        else:
            logger.warning(f"Unknown modifier: {transform}, skipping")

    return result


# ============================================================================
# Basic Arithmetic Modifiers
# ============================================================================

def modify_multiply(values: np.ndarray, factor: float) -> np.ndarray:
    """Multiply values by constant factor."""
    return values * factor


def modify_add(values: np.ndarray, value: float) -> np.ndarray:
    """Add constant value."""
    return values + value


def modify_clamp(values: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
    """Clamp values to range."""
    return np.clip(values, min_val, max_val)


# ============================================================================
# Noise Modifiers
# ============================================================================

def modify_jitter(
    values: np.ndarray,
    rng: np.random.Generator,
    std: float,
    mode: str = "add"
) -> np.ndarray:
    """
    Add random noise to values.

    Args:
        values: Input values
        rng: Random generator
        std: Standard deviation of noise
        mode: "add" (additive) or "mul" (multiplicative)

    Returns:
        Jittered values
    """
    noise = rng.normal(0, std, size=len(values))

    if mode == "add":
        return values + noise
    elif mode == "mul":
        return values * (1.0 + noise)
    else:
        raise ValueError(f"Unknown jitter mode: {mode}")


def modify_time_jitter(
    timestamps: np.ndarray,
    rng: np.random.Generator,
    std_minutes: float
) -> np.ndarray:
    """
    Add random jitter to timestamps.

    Args:
        timestamps: Datetime values
        rng: Random generator
        std_minutes: Standard deviation in minutes

    Returns:
        Jittered timestamps
    """
    timestamps = pd.to_datetime(timestamps)

    # Generate jitter in minutes
    jitter_minutes = rng.normal(0, std_minutes, size=len(timestamps))

    # Convert to timedelta and add
    jitter_td = pd.to_timedelta(jitter_minutes, unit='m')
    return timestamps + jitter_td


# ============================================================================
# Categorical Modifiers
# ============================================================================

def modify_map_values(values: np.ndarray, mapping: dict) -> np.ndarray:
    """
    Map values through a dictionary.

    Args:
        values: Input values
        mapping: {old_value: new_value} dictionary

    Returns:
        Mapped values
    """
    result = values.copy()

    for old_val, new_val in mapping.items():
        result[result == old_val] = new_val

    return result


# ============================================================================
# Temporal Modifiers
# ============================================================================

def modify_seasonality(
    values: np.ndarray,
    timestamps: pd.Series,
    dimension: str,
    weights: list[float]
) -> np.ndarray:
    """
    Apply seasonality multipliers based on time.

    Args:
        values: Numeric values to scale
        timestamps: Timestamps
        dimension: "hour", "dow", or "month"
        weights: Multipliers for each time component

    Returns:
        Scaled values
    """
    multipliers = get_seasonality_multiplier(timestamps, dimension, weights)
    return values * multipliers


def modify_trend(
    values: np.ndarray,
    timestamps: pd.Series,
    trend_type: str,
    growth_rate: Optional[float] = None,
    params: Optional[dict] = None
) -> np.ndarray:
    """
    Apply time-based trend (growth or decay) to values.

    Args:
        values: Numeric values to scale
        timestamps: Timestamps for trend calculation
        trend_type: "exponential", "linear", or "logarithmic"
        growth_rate: Annual growth rate (e.g., 0.08 for 8% growth) for exponential/linear
        params: Additional parameters for specific trend types

    Returns:
        Values with trend applied
    """
    timestamps = pd.to_datetime(timestamps)

    # Calculate time delta from start (in years for growth rate)
    start_time = timestamps.min()
    time_delta_days = (timestamps - start_time).dt.total_seconds() / (24 * 3600)
    time_delta_years = time_delta_days / 365.25

    if trend_type == "exponential":
        # Exponential growth: value * (1 + growth_rate) ^ t
        if growth_rate is None:
            raise ValueError("exponential trend requires growth_rate")
        multipliers = np.power(1 + growth_rate, time_delta_years)

    elif trend_type == "linear":
        # Linear growth: value * (1 + growth_rate * t)
        if growth_rate is None:
            raise ValueError("linear trend requires growth_rate")
        multipliers = 1 + growth_rate * time_delta_years

    elif trend_type == "logarithmic":
        # Logarithmic growth: value * (1 + a * log(1 + b * t))
        # Default params: a=0.1, b=1.0
        if params is None:
            params = {}
        a = params.get("a", 0.1)
        b = params.get("b", 1.0)
        multipliers = 1 + a * np.log(1 + b * time_delta_years)

    else:
        raise ValueError(f"Unknown trend type: {trend_type}. Must be 'exponential', 'linear', or 'logarithmic'")

    return values * multipliers


def modify_effect(
    values: np.ndarray,
    context: pd.DataFrame,
    effect_table_name: str,
    on: dict,
    window: dict,
    map_spec: dict
) -> np.ndarray:
    """
    Apply time-windowed effects from external event table.

    Args:
        values: Numeric values to modify
        context: DataFrame with current row data including effect table reference
        effect_table_name: Name of effect table
        on: Join keys {local_key: effect_key}
        window: Window spec {start_col, end_col}
        map_spec: Mapping spec {field, op, default}

    Returns:
        Modified values with effects applied

    Example:
        effect_table has: promotion_id, start_at, end_at, discount_multiplier
        context has: promotion_id, order_time, _effect_promotion (DataFrame)
        on: {promotion_id: promotion_id}
        window: {start_col: start_at, end_col: end_at}
        map: {field: discount_multiplier, op: mul, default: 1.0}
    """
    # Get effect table DataFrame from context
    effect_col = f"_effect_{effect_table_name}"
    if effect_col not in context.columns:
        logger.warning(f"Effect table {effect_table_name} not found in context")
        return values

    # Extract parameters
    start_col = window["start_col"]
    end_col = window["end_col"]
    field = map_spec["field"]
    op = map_spec["op"]
    default = map_spec["default"]

    # Find timestamp column in context for window matching
    timestamp_col = None
    for col in context.columns:
        if col.startswith("_effect_"):
            continue
        if pd.api.types.is_datetime64_any_dtype(context[col]):
            timestamp_col = col
            break

    if timestamp_col is None:
        logger.warning("Effect modifier requires datetime column in context for window matching")
        return values

    # Get timestamps
    timestamps = pd.to_datetime(context[timestamp_col])

    # Initialize result with default values
    result = np.full(len(values), default, dtype=float)

    # Get the effect table (stored as a single value in each row)
    effect_df = context[effect_col].iloc[0]

    # For each row, find matching effects
    for idx in range(len(values)):
        row_timestamp = timestamps.iloc[idx]

        # Filter effects by join keys
        matching_effects = effect_df.copy()

        if on:  # If there are join keys
            for local_key, effect_key in on.items():
                if local_key not in context.columns:
                    continue
                local_value = context[local_key].iloc[idx]
                matching_effects = matching_effects[matching_effects[effect_key] == local_value]

        # Filter by time window
        if start_col in matching_effects.columns and end_col in matching_effects.columns:
            matching_effects = matching_effects[
                (pd.to_datetime(matching_effects[start_col]) <= row_timestamp) &
                (pd.to_datetime(matching_effects[end_col]) >= row_timestamp)
            ]

        # Apply effect if found
        if len(matching_effects) > 0 and field in matching_effects.columns:
            # Use first matching effect (could aggregate multiple effects)
            effect_value = matching_effects[field].iloc[0]
            result[idx] = effect_value

    # Apply operation
    if op == "mul":
        return values * result
    elif op == "add":
        return values + result
    else:
        logger.warning(f"Unknown effect operation: {op}")
        return values


# ============================================================================
# Outlier Injection
# ============================================================================

def modify_outliers(
    values: np.ndarray,
    rng: np.random.Generator,
    rate: float,
    mode: str,
    magnitude_dist: dict
) -> np.ndarray:
    """
    Inject outliers into values.

    Args:
        values: Input values
        rng: Random generator
        rate: Fraction of values to make outliers (e.g., 0.01 = 1%)
        mode: "spike" (increase) or "drop" (decrease)
        magnitude_dist: Distribution spec for magnitude {type, params}

    Returns:
        Values with outliers injected
    """
    n = len(values)
    n_outliers = int(n * rate)

    if n_outliers == 0:
        return values

    # Select random indices for outliers
    outlier_indices = rng.choice(n, size=n_outliers, replace=False)

    # Generate magnitude multipliers
    from datagen.core.generators.primitives import generate_distribution

    magnitudes = generate_distribution(
        magnitude_dist["type"],
        magnitude_dist["params"],
        n_outliers,
        rng,
        clamp=magnitude_dist.get("clamp", [0.1, 10.0])
    )

    result = values.copy()

    if mode == "spike":
        # Multiply by magnitude > 1
        result[outlier_indices] *= (1.0 + magnitudes)
    elif mode == "drop":
        # Divide by magnitude
        result[outlier_indices] /= (1.0 + magnitudes)
    else:
        raise ValueError(f"Unknown outlier mode: {mode}")

    return result

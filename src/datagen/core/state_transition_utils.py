"""
Utility functions for state transition modeling (Feature #4).

Supports:
- Subscription lifecycle (trial → active → churned)
- Recurring relationships with state changes
- Churn and reactivation patterns
- Segment-based transition rate variations
- Vintage effects on transition probabilities
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def simulate_state_transitions(
    parent_df: pd.DataFrame,
    state_model: dict,
    parent_id_col: str,
    parent_created_at_col: Optional[str] = None,
    parent_segment_col: Optional[str] = None,
    timeframe_start: Optional[pd.Timestamp] = None,
    timeframe_end: Optional[pd.Timestamp] = None,
    vintage_behavior: Optional[dict] = None,
    rng: np.random.Generator = None
) -> pd.DataFrame:
    """
    Simulate state transitions for parent entities using Markov chain.

    Args:
        parent_df: Parent DataFrame (e.g., customers, members)
        state_model: State transition model configuration
        parent_id_col: Column name for parent entity ID
        parent_created_at_col: Optional column name for entity creation timestamp
        parent_segment_col: Optional column name for segment
        timeframe_start: Start of timeframe for transitions
        timeframe_end: End of timeframe for transitions
        vintage_behavior: Optional vintage effects configuration
        rng: Random number generator

    Returns:
        DataFrame with state transition events:
        - parent_id: ID of parent entity
        - transition_time: Timestamp of state change
        - from_state: Previous state (None for initial)
        - to_state: New state
        - transition_index: Sequence number (0, 1, 2, ...)

    Example state_model:
        {
            "initial_state": "active",
            "states": {
                "active": {
                    "transition_prob_per_period": 0.05,
                    "next_states": {
                        "churned": 0.60,
                        "paused": 0.40
                    }
                },
                "paused": {
                    "transition_prob_per_period": 0.30,
                    "next_states": {
                        "active": 0.50,
                        "churned": 0.50
                    }
                },
                "churned": {
                    "terminal": true
                }
            },
            "period_unit": "month",
            "max_transitions": 20,
            "segment_variation": {
                "vip": {"churn_multiplier": 0.4}
            },
            "vintage_variation": {
                "churn_multiplier_curve": [1.0, 0.8, 0.7, 0.6]
            }
        }
    """
    if rng is None:
        rng = np.random.default_rng()

    # Extract state model config
    initial_state = state_model.get("initial_state")
    states = state_model.get("states", {})
    period_unit = state_model.get("period_unit", "month")
    max_transitions = state_model.get("max_transitions", 50)
    segment_variation = state_model.get("segment_variation", {})
    vintage_variation = state_model.get("vintage_variation", {})

    if not initial_state or not states:
        raise ValueError("state_model must have 'initial_state' and 'states'")

    # Convert period_unit to days
    period_days = {
        "day": 1,
        "week": 7,
        "month": 30,
        "year": 365
    }.get(period_unit, 30)

    # Collect all transition events
    all_transitions = []

    for parent_idx in range(len(parent_df)):
        parent_id = parent_df.iloc[parent_idx][parent_id_col]

        # Get parent created_at (start of their timeline)
        if parent_created_at_col and parent_created_at_col in parent_df.columns:
            start_time = parent_df.iloc[parent_idx][parent_created_at_col]
        elif timeframe_start:
            start_time = timeframe_start
        else:
            # Fallback: use current time
            start_time = pd.Timestamp.now()

        # Get segment for this parent
        segment = None
        if parent_segment_col and parent_segment_col in parent_df.columns:
            segment = parent_df.iloc[parent_idx][parent_segment_col]

        # Simulate transitions for this parent
        transitions = _simulate_entity_transitions(
            parent_id=parent_id,
            start_time=start_time,
            end_time=timeframe_end,
            initial_state=initial_state,
            states=states,
            period_days=period_days,
            max_transitions=max_transitions,
            segment=segment,
            segment_variation=segment_variation,
            vintage_behavior=vintage_behavior,
            rng=rng
        )

        all_transitions.extend(transitions)

    # Convert to DataFrame
    if not all_transitions:
        # Return empty DataFrame with expected schema
        return pd.DataFrame(columns=[
            parent_id_col, "transition_time", "from_state", "to_state", "transition_index"
        ])

    df = pd.DataFrame(all_transitions)
    df = df.rename(columns={"parent_id": parent_id_col})

    return df


def _simulate_entity_transitions(
    parent_id,
    start_time: pd.Timestamp,
    end_time: Optional[pd.Timestamp],
    initial_state: str,
    states: dict,
    period_days: int,
    max_transitions: int,
    segment: Optional[str],
    segment_variation: dict,
    vintage_behavior: Optional[dict],
    rng: np.random.Generator
) -> List[dict]:
    """
    Simulate state transitions for a single entity.

    Returns list of transition events.
    """
    transitions = []
    current_state = initial_state
    current_time = start_time
    transition_index = 0

    # Record initial state
    transitions.append({
        "parent_id": parent_id,
        "transition_time": current_time,
        "from_state": None,  # No previous state for initial
        "to_state": current_state,
        "transition_index": transition_index
    })

    # Simulate transitions until terminal state or limits reached
    while transition_index < max_transitions:
        state_config = states.get(current_state, {})

        # Check if terminal state
        if state_config.get("terminal", False):
            break

        # Get transition probability
        base_prob = state_config.get("transition_prob_per_period", 0.0)

        if base_prob <= 0:
            # No transitions from this state
            break

        # Apply multipliers
        effective_prob = base_prob

        # Segment multiplier (affects churn/transition rates)
        if segment and segment in segment_variation:
            churn_mult = segment_variation[segment].get("churn_multiplier", 1.0)
            effective_prob = effective_prob * churn_mult

        # Vintage multiplier (based on entity age)
        if vintage_behavior:
            entity_age_days = (current_time - start_time).days
            entity_age_periods = entity_age_days / period_days

            # Apply vintage curve if configured
            if "churn_multiplier_curve" in vintage_behavior:
                curve = vintage_behavior["churn_multiplier_curve"]
                period_idx = int(entity_age_periods)

                if period_idx < len(curve):
                    vintage_mult = curve[period_idx]
                else:
                    # Use last value for older entities
                    vintage_mult = curve[-1]

                effective_prob = effective_prob * vintage_mult

        # Cap probability at 1.0
        effective_prob = min(1.0, effective_prob)

        # Sample time until next transition (exponential distribution)
        # Mean time = period_days / effective_prob
        if effective_prob > 0:
            mean_time = period_days / effective_prob
            time_until_transition = rng.exponential(mean_time)
        else:
            # No transitions
            break

        # Calculate next transition time
        next_time = current_time + pd.Timedelta(days=time_until_transition)

        # Check if exceeds timeframe
        if end_time:
            # Ensure both are comparable (same timezone awareness)
            try:
                if next_time > end_time:
                    break
            except TypeError:
                # Timezone mismatch - convert next_time to match end_time
                if hasattr(end_time, 'tz') and end_time.tz is not None:
                    next_time = next_time.tz_localize('UTC')
                if next_time > end_time:
                    break

        # Sample next state
        next_states = state_config.get("next_states", {})
        if not next_states:
            # No possible transitions
            break

        # Convert to arrays for sampling
        next_state_names = list(next_states.keys())
        next_state_probs = list(next_states.values())

        # Normalize probabilities
        total_prob = sum(next_state_probs)
        if total_prob <= 0:
            break

        next_state_probs = [p / total_prob for p in next_state_probs]

        # Sample next state
        next_state = rng.choice(next_state_names, p=next_state_probs)

        # Record transition
        transition_index += 1
        transitions.append({
            "parent_id": parent_id,
            "transition_time": next_time,
            "from_state": current_state,
            "to_state": next_state,
            "transition_index": transition_index
        })

        # Update state
        current_state = next_state
        current_time = next_time

    return transitions


def get_current_states(
    transition_df: pd.DataFrame,
    parent_id_col: str
) -> pd.DataFrame:
    """
    Get current (latest) state for each parent entity.

    Args:
        transition_df: DataFrame from simulate_state_transitions
        parent_id_col: Column name for parent entity ID

    Returns:
        DataFrame with columns:
        - parent_id
        - current_state
        - state_changed_at (timestamp of last transition)
        - total_transitions (count of transitions)
    """
    if transition_df.empty:
        return pd.DataFrame(columns=[
            parent_id_col, "current_state", "state_changed_at", "total_transitions"
        ])

    # Get latest transition for each parent
    latest = (
        transition_df
        .sort_values("transition_time")
        .groupby(parent_id_col)
        .tail(1)
        .copy()
    )

    # Count total transitions
    transition_counts = (
        transition_df
        .groupby(parent_id_col)
        .size()
        .reset_index(name="total_transitions")
    )

    # Merge
    result = latest[[parent_id_col, "to_state", "transition_time"]].merge(
        transition_counts,
        on=parent_id_col,
        how="left"
    )

    result = result.rename(columns={
        "to_state": "current_state",
        "transition_time": "state_changed_at"
    })

    return result


def calculate_state_statistics(
    transition_df: pd.DataFrame,
    parent_id_col: str
) -> Dict:
    """
    Calculate summary statistics about state transitions.

    Args:
        transition_df: DataFrame from simulate_state_transitions
        parent_id_col: Column name for parent entity ID

    Returns:
        Dictionary with statistics:
        - total_entities: Count of unique entities
        - total_transitions: Count of transition events
        - state_distribution: Count per state
        - transition_matrix: From/to state counts
        - avg_transitions_per_entity: Mean transitions
    """
    if transition_df.empty:
        return {
            "total_entities": 0,
            "total_transitions": 0,
            "state_distribution": {},
            "transition_matrix": {},
            "avg_transitions_per_entity": 0
        }

    total_entities = transition_df[parent_id_col].nunique()
    total_transitions = len(transition_df)

    # Current state distribution
    current_states = get_current_states(transition_df, parent_id_col)
    state_dist = current_states["current_state"].value_counts().to_dict()

    # Transition matrix (from_state → to_state counts)
    transitions_only = transition_df[transition_df["from_state"].notna()].copy()

    if not transitions_only.empty:
        transition_matrix = (
            transitions_only
            .groupby(["from_state", "to_state"])
            .size()
            .reset_index(name="count")
            .to_dict('records')
        )
    else:
        transition_matrix = []

    # Average transitions per entity
    avg_transitions = (
        transition_df
        .groupby(parent_id_col)
        .size()
        .mean()
    )

    return {
        "total_entities": int(total_entities),
        "total_transitions": int(total_transitions),
        "state_distribution": {k: int(v) for k, v in state_dist.items()},
        "transition_matrix": transition_matrix,
        "avg_transitions_per_entity": float(avg_transitions)
    }

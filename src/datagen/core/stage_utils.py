"""
Utility functions for multi-stage process generation (Feature #3).

Supports:
- Conversion funnels (signup → activation → purchase)
- User journey progression
- Stage-based drop-off
- Segment-based transition rate variations
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_stage_progression(
    parent_df: pd.DataFrame,
    stage_config: dict,
    parent_segment_col: Optional[str] = None,
    rng: np.random.Generator = None
) -> pd.DataFrame:
    """
    Calculate which stage each parent entity reaches in a multi-stage process.

    Args:
        parent_df: Parent DataFrame (e.g., users)
        stage_config: Stage configuration with stages and transition rates
        parent_segment_col: Optional column name for segments
        rng: Random number generator

    Returns:
        DataFrame with columns:
        - parent_index: Index of parent entity
        - stage_reached: Name of final stage reached
        - stage_index: Numeric index of final stage reached (0-based)

    Example stage_config:
        {
            "stages": [
                {"stage_name": "signup", "transition_rate": 1.0},
                {"stage_name": "activation", "transition_rate": 0.35},
                {"stage_name": "purchase", "transition_rate": 0.80}
            ],
            "segment_variation": {
                "vip": {"transition_multiplier": 1.3},
                "budget": {"transition_multiplier": 0.7}
            }
        }
    """
    if rng is None:
        rng = np.random.default_rng()

    stages = stage_config.get("stages", [])
    if not stages:
        raise ValueError("stage_config must have 'stages' list")

    segment_variation = stage_config.get("segment_variation", {})

    n_parents = len(parent_df)
    results = []

    for parent_idx in range(n_parents):
        # Get segment if available
        segment = None
        if parent_segment_col and parent_segment_col in parent_df.columns:
            segment = parent_df.iloc[parent_idx][parent_segment_col]

        # Get transition multiplier for this segment
        transition_multiplier = 1.0
        if segment and segment in segment_variation:
            transition_multiplier = segment_variation[segment].get("transition_multiplier", 1.0)

        # Simulate progression through stages
        current_stage_index = 0
        for stage_idx, stage in enumerate(stages):
            # First stage always reached (transition_rate=1.0 for signup/start)
            if stage_idx == 0:
                current_stage_index = 0
                continue

            # Calculate effective transition rate
            base_rate = stage["transition_rate"]
            effective_rate = min(1.0, base_rate * transition_multiplier)

            # Roll dice to see if transition happens
            if rng.random() < effective_rate:
                current_stage_index = stage_idx
            else:
                # Drop off - don't progress further
                break

        results.append({
            "parent_index": parent_idx,
            "stage_reached": stages[current_stage_index]["stage_name"],
            "stage_index": current_stage_index
        })

    return pd.DataFrame(results)


def generate_stage_events(
    parent_df: pd.DataFrame,
    stage_progression: pd.DataFrame,
    stage_config: dict,
    pk_start: int = 1,
    timestamp_col: Optional[str] = None,
    time_between_stages_hours: float = 24.0,
    rng: np.random.Generator = None
) -> pd.DataFrame:
    """
    Generate event records for each stage reached by parent entities.

    Args:
        parent_df: Parent DataFrame
        stage_progression: Output from calculate_stage_progression
        stage_config: Stage configuration
        pk_start: Starting value for primary key
        timestamp_col: Optional timestamp column in parent_df for temporal ordering
        time_between_stages_hours: Average time between stages (hours)
        rng: Random number generator

    Returns:
        DataFrame with one row per stage event, including:
        - event_id: Primary key
        - parent_id: Foreign key to parent
        - stage_name: Name of the stage
        - stage_index: Numeric index of stage (0-based)
        - timestamp: Optional timestamp of stage event
    """
    if rng is None:
        rng = np.random.default_rng()

    stages = stage_config.get("stages", [])
    records = []
    event_id = pk_start

    for _, row in stage_progression.iterrows():
        parent_idx = row["parent_index"]
        final_stage_index = row["stage_index"]

        # Generate events for all stages reached (including final one)
        for stage_idx in range(final_stage_index + 1):
            stage_name = stages[stage_idx]["stage_name"]

            # Calculate timestamp if parent has timestamp column
            timestamp = None
            if timestamp_col and timestamp_col in parent_df.columns:
                parent_timestamp = parent_df.iloc[parent_idx][timestamp_col]

                # Add time offset for each stage
                # First stage happens at parent timestamp, subsequent stages later
                if stage_idx > 0:
                    # Add random jitter around average time between stages
                    hours_offset = rng.exponential(time_between_stages_hours * stage_idx)
                    timestamp = parent_timestamp + pd.Timedelta(hours=hours_offset)
                else:
                    timestamp = parent_timestamp

            record = {
                "event_id": event_id,
                "parent_index": parent_idx,
                "stage_name": stage_name,
                "stage_index": stage_idx
            }

            if timestamp is not None:
                record["timestamp"] = timestamp

            records.append(record)
            event_id += 1

    return pd.DataFrame(records)


def get_stage_statistics(stage_progression: pd.DataFrame, stage_config: dict) -> Dict:
    """
    Calculate funnel statistics from stage progression data.

    Args:
        stage_progression: Output from calculate_stage_progression
        stage_config: Stage configuration

    Returns:
        Dictionary with funnel statistics:
        - total_entities: Total number of entities
        - stage_counts: Count of entities reaching each stage
        - stage_rates: Percentage of entities reaching each stage
        - drop_off_rates: Drop-off rate between consecutive stages
    """
    stages = stage_config.get("stages", [])
    total = len(stage_progression)

    stage_counts = {}
    for stage in stages:
        count = (stage_progression["stage_reached"] == stage["stage_name"]).sum()
        stage_counts[stage["stage_name"]] = int(count)

    # Calculate cumulative counts (entities reaching at least this stage)
    cumulative_counts = {}
    for stage_idx, stage in enumerate(stages):
        count = (stage_progression["stage_index"] >= stage_idx).sum()
        cumulative_counts[stage["stage_name"]] = int(count)

    # Calculate rates
    stage_rates = {}
    for stage_name, count in cumulative_counts.items():
        stage_rates[stage_name] = round(count / total, 3) if total > 0 else 0

    # Calculate drop-off rates
    drop_off_rates = {}
    for i in range(1, len(stages)):
        prev_stage = stages[i - 1]["stage_name"]
        curr_stage = stages[i]["stage_name"]

        prev_count = cumulative_counts[prev_stage]
        curr_count = cumulative_counts[curr_stage]

        if prev_count > 0:
            drop_off_rates[f"{prev_stage}_to_{curr_stage}"] = round(
                1 - (curr_count / prev_count), 3
            )
        else:
            drop_off_rates[f"{prev_stage}_to_{curr_stage}"] = 0

    return {
        "total_entities": total,
        "stage_counts": stage_counts,
        "cumulative_counts": cumulative_counts,
        "stage_rates": stage_rates,
        "drop_off_rates": drop_off_rates
    }

"""
Tests for Feature #5: Multi-Touch Attribution Chains
"""

import pytest
import numpy as np
import pandas as pd
from src.datagen.core.attribution_chain_utils import (
    generate_attribution_chains,
    calculate_attribution_weights,
    validate_attribution_chain
)


class TestAttributionWeights:
    """Test attribution weight calculation models."""

    def test_linear_attribution(self):
        """Linear model gives equal credit to all touchpoints."""
        weights = calculate_attribution_weights(
            n_touches=4,
            model="linear",
            days_before=np.array([20, 15, 10, 5]),
            halflife_days=7
        )

        assert len(weights) == 4
        assert np.allclose(weights, [0.25, 0.25, 0.25, 0.25])
        assert np.isclose(weights.sum(), 1.0)

    def test_first_touch_attribution(self):
        """First touch model gives 100% credit to first touchpoint."""
        weights = calculate_attribution_weights(
            n_touches=4,
            model="first_touch",
            days_before=np.array([20, 15, 10, 5]),
            halflife_days=7
        )

        assert len(weights) == 4
        assert weights[0] == 1.0
        assert np.allclose(weights[1:], 0.0)
        assert np.isclose(weights.sum(), 1.0)

    def test_last_touch_attribution(self):
        """Last touch model gives 100% credit to last touchpoint."""
        weights = calculate_attribution_weights(
            n_touches=4,
            model="last_touch",
            days_before=np.array([20, 15, 10, 5]),
            halflife_days=7
        )

        assert len(weights) == 4
        assert weights[-1] == 1.0
        assert np.allclose(weights[:-1], 0.0)
        assert np.isclose(weights.sum(), 1.0)

    def test_time_decay_attribution(self):
        """Time decay model gives more credit to recent touchpoints."""
        weights = calculate_attribution_weights(
            n_touches=4,
            model="time_decay",
            days_before=np.array([20, 15, 10, 5]),  # Oldest to newest
            halflife_days=7
        )

        assert len(weights) == 4
        # More recent touchpoints should have higher weight
        assert weights[0] < weights[-1]
        # Weights should decrease monotonically going backwards
        assert weights[0] < weights[1] < weights[2] < weights[3]
        assert np.isclose(weights.sum(), 1.0)

    def test_single_touchpoint(self):
        """Single touchpoint gets 100% credit in all models."""
        for model in ["linear", "first_touch", "last_touch", "time_decay"]:
            weights = calculate_attribution_weights(
                n_touches=1,
                model=model,
                days_before=np.array([10]),
                halflife_days=7
            )

            assert len(weights) == 1
            assert weights[0] == 1.0


class TestAttributionChainGeneration:
    """Test attribution chain generation."""

    def test_generates_touchpoints_for_conversions(self):
        """Should generate touchpoints for each conversion."""
        conversions = pd.DataFrame({
            "order_id": [1, 2, 3],
            "customer_id": [101, 102, 103],
            "timestamp": pd.to_datetime(["2024-01-15", "2024-01-20", "2024-01-25"])
        })

        touchpoints = generate_attribution_chains(
            conversion_df=conversions,
            conversion_id_col="order_id",
            conversion_time_col="timestamp",
            touchpoint_channels=["email", "social", "paid_search"],
            min_touches=2,
            max_touches=4,
            time_window_days=30,
            attribution_model="linear",
            rng=np.random.default_rng(42)
        )

        # Should have touchpoints for all conversions
        assert len(touchpoints) > 0
        assert set(touchpoints["conversion_id"]) == {1, 2, 3}

        # Each conversion should have 2-4 touchpoints
        counts = touchpoints.groupby("conversion_id").size()
        assert all(2 <= count <= 4 for count in counts)

    def test_touchpoint_timestamps_before_conversion(self):
        """Touchpoint timestamps should be before conversion."""
        conversions = pd.DataFrame({
            "order_id": [1],
            "timestamp": pd.to_datetime(["2024-01-15"])
        })

        touchpoints = generate_attribution_chains(
            conversion_df=conversions,
            conversion_id_col="order_id",
            conversion_time_col="timestamp",
            touchpoint_channels=["email", "social"],
            min_touches=3,
            max_touches=3,
            time_window_days=30,
            attribution_model="linear",
            rng=np.random.default_rng(42)
        )

        conversion_time = conversions.iloc[0]["timestamp"]
        assert all(touchpoints["timestamp"] <= conversion_time)

    def test_attribution_weights_sum_to_one(self):
        """Attribution weights per conversion should sum to 1.0."""
        conversions = pd.DataFrame({
            "order_id": [1, 2],
            "timestamp": pd.to_datetime(["2024-01-15", "2024-01-20"])
        })

        touchpoints = generate_attribution_chains(
            conversion_df=conversions,
            conversion_id_col="order_id",
            conversion_time_col="timestamp",
            touchpoint_channels=["email", "social"],
            min_touches=2,
            max_touches=4,
            time_window_days=30,
            attribution_model="linear",
            rng=np.random.default_rng(42)
        )

        weight_sums = touchpoints.groupby("conversion_id")["attribution_weight"].sum()
        assert all(np.isclose(weight_sums, 1.0))

    def test_deterministic_with_seed(self):
        """Same seed should produce same touchpoints."""
        conversions = pd.DataFrame({
            "order_id": [1],
            "timestamp": pd.to_datetime(["2024-01-15"])
        })

        touchpoints1 = generate_attribution_chains(
            conversion_df=conversions,
            conversion_id_col="order_id",
            conversion_time_col="timestamp",
            touchpoint_channels=["email", "social"],
            min_touches=3,
            max_touches=3,
            time_window_days=30,
            attribution_model="linear",
            rng=np.random.default_rng(42)
        )

        touchpoints2 = generate_attribution_chains(
            conversion_df=conversions,
            conversion_id_col="order_id",
            conversion_time_col="timestamp",
            touchpoint_channels=["email", "social"],
            min_touches=3,
            max_touches=3,
            time_window_days=30,
            attribution_model="linear",
            rng=np.random.default_rng(42)
        )

        pd.testing.assert_frame_equal(touchpoints1, touchpoints2)

    def test_position_field_correct(self):
        """Position field should be 1-indexed and sequential."""
        conversions = pd.DataFrame({
            "order_id": [1],
            "timestamp": pd.to_datetime(["2024-01-15"])
        })

        touchpoints = generate_attribution_chains(
            conversion_df=conversions,
            conversion_id_col="order_id",
            conversion_time_col="timestamp",
            touchpoint_channels=["email"],
            min_touches=3,
            max_touches=3,
            time_window_days=30,
            attribution_model="linear",
            rng=np.random.default_rng(42)
        )

        positions = touchpoints.sort_values("touchpoint_id")["position"].values
        assert list(positions) == [1, 2, 3]


class TestAttributionValidation:
    """Test attribution chain validation."""

    def test_valid_attribution_chain(self):
        """Valid attribution chain passes all checks."""
        conversions = pd.DataFrame({
            "order_id": [1, 2],
            "timestamp": pd.to_datetime(["2024-01-15", "2024-01-20"])
        })

        touchpoints = pd.DataFrame({
            "touchpoint_id": [1, 2, 3, 4],
            "conversion_id": [1, 1, 2, 2],
            "channel": ["email", "social", "email", "paid_search"],
            "timestamp": pd.to_datetime(["2024-01-10", "2024-01-14", "2024-01-15", "2024-01-19"]),
            "attribution_weight": [0.5, 0.5, 0.6, 0.4]
        })

        result = validate_attribution_chain(touchpoints, conversions, "order_id")

        assert result["valid"]
        assert len(result["issues"]) == 0
        assert result["total_conversions"] == 2
        assert result["total_touchpoints"] == 4
        assert result["avg_touchpoints_per_conversion"] == 2.0

    def test_detects_orphaned_touchpoints(self):
        """Should detect touchpoints without matching conversion."""
        conversions = pd.DataFrame({
            "order_id": [1],
            "timestamp": pd.to_datetime(["2024-01-15"])
        })

        touchpoints = pd.DataFrame({
            "touchpoint_id": [1, 2],
            "conversion_id": [1, 999],  # 999 doesn't exist
            "timestamp": pd.to_datetime(["2024-01-10", "2024-01-14"]),
            "attribution_weight": [1.0, 1.0]
        })

        result = validate_attribution_chain(touchpoints, conversions, "order_id")

        assert not result["valid"]
        assert any("orphaned" in issue.lower() for issue in result["issues"])

    def test_detects_invalid_weight_sums(self):
        """Should detect attribution weights not summing to 1.0."""
        conversions = pd.DataFrame({
            "order_id": [1],
            "timestamp": pd.to_datetime(["2024-01-15"])
        })

        touchpoints = pd.DataFrame({
            "touchpoint_id": [1, 2],
            "conversion_id": [1, 1],
            "timestamp": pd.to_datetime(["2024-01-10", "2024-01-14"]),
            "attribution_weight": [0.3, 0.5]  # Sums to 0.8, not 1.0
        })

        result = validate_attribution_chain(touchpoints, conversions, "order_id")

        assert not result["valid"]
        assert any("not summing to 1.0" in issue for issue in result["issues"])

    def test_detects_temporal_violations(self):
        """Should detect touchpoints after conversion time."""
        conversions = pd.DataFrame({
            "order_id": [1],
            "timestamp": pd.to_datetime(["2024-01-15"])
        })

        touchpoints = pd.DataFrame({
            "touchpoint_id": [1, 2],
            "conversion_id": [1, 1],
            "timestamp": pd.to_datetime(["2024-01-10", "2024-01-20"]),  # 2nd after conversion
            "attribution_weight": [0.5, 0.5]
        })

        result = validate_attribution_chain(touchpoints, conversions, "order_id")

        assert not result["valid"]
        assert any("after conversion time" in issue for issue in result["issues"])

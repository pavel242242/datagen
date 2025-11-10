"""Additional tests for modifier functions to improve coverage."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from datagen.core.modifiers import (
    modify_multiply,
    modify_add,
    modify_clamp,
    modify_jitter,
    modify_time_jitter,
    modify_map_values,
    modify_seasonality,
    modify_outliers,
    apply_modifiers
)


class TestBasicArithmeticModifiers:
    """Tests for multiply, add, and clamp modifiers."""

    def test_modify_multiply(self):
        """Test multiply modifier."""
        values = np.array([10.0, 20.0, 30.0, 40.0])
        result = modify_multiply(values, 2.5)

        expected = np.array([25.0, 50.0, 75.0, 100.0])
        assert np.allclose(result, expected)

    def test_modify_multiply_negative_factor(self):
        """Test multiply with negative factor."""
        values = np.array([10.0, 20.0, 30.0])
        result = modify_multiply(values, -1.0)

        expected = np.array([-10.0, -20.0, -30.0])
        assert np.allclose(result, expected)

    def test_modify_add(self):
        """Test add modifier."""
        values = np.array([10.0, 20.0, 30.0, 40.0])
        result = modify_add(values, 5.0)

        expected = np.array([15.0, 25.0, 35.0, 45.0])
        assert np.allclose(result, expected)

    def test_modify_add_negative(self):
        """Test add with negative value."""
        values = np.array([10.0, 20.0, 30.0])
        result = modify_add(values, -5.0)

        expected = np.array([5.0, 15.0, 25.0])
        assert np.allclose(result, expected)

    def test_modify_clamp_both_bounds(self):
        """Test clamp modifier with both bounds."""
        values = np.array([5.0, 15.0, 25.0, 35.0, 45.0])
        result = modify_clamp(values, 10.0, 40.0)

        expected = np.array([10.0, 15.0, 25.0, 35.0, 40.0])
        assert np.allclose(result, expected)

    def test_modify_clamp_min_only(self):
        """Test clamp with minimum only."""
        values = np.array([5.0, 15.0, 25.0, 35.0])
        result = modify_clamp(values, 20.0, np.inf)

        assert all(result >= 20.0)
        assert result[2] == 25.0  # Unchanged
        assert result[3] == 35.0  # Unchanged

    def test_modify_clamp_max_only(self):
        """Test clamp with maximum only."""
        values = np.array([5.0, 15.0, 25.0, 35.0])
        result = modify_clamp(values, -np.inf, 20.0)

        assert all(result <= 20.0)
        assert result[0] == 5.0   # Unchanged
        assert result[1] == 15.0  # Unchanged


class TestNoiseModifiers:
    """Tests for jitter and time_jitter modifiers."""

    def test_modify_jitter_additive(self):
        """Test additive jitter modifier."""
        rng = np.random.default_rng(42)
        values = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        result = modify_jitter(values, rng, std=5.0, mode="add")

        # Result should be close to 100 but not exactly 100
        assert not np.allclose(result, values)
        # Mean should be close to 100
        assert 90 < result.mean() < 110
        # Standard deviation should be around 5
        assert 3 < result.std() < 7

    def test_modify_jitter_multiplicative(self):
        """Test multiplicative jitter modifier."""
        rng = np.random.default_rng(42)
        values = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        result = modify_jitter(values, rng, std=0.1, mode="mul")

        # Result should vary around 100
        assert not np.allclose(result, values)
        # Mean should be close to 100
        assert 90 < result.mean() < 110

    def test_modify_jitter_invalid_mode(self):
        """Test that invalid jitter mode raises error."""
        rng = np.random.default_rng(42)
        values = np.array([100.0, 100.0, 100.0])

        with pytest.raises(ValueError, match="Unknown jitter mode"):
            modify_jitter(values, rng, std=5.0, mode="invalid")

    def test_modify_time_jitter(self):
        """Test time jitter modifier."""
        rng = np.random.default_rng(42)

        # Create timestamps
        base_time = pd.Timestamp("2024-01-01 12:00:00")
        timestamps = np.array([base_time] * 5)

        result = modify_time_jitter(timestamps, rng, std_minutes=30.0)

        # Result should be datetime
        assert pd.api.types.is_datetime64_any_dtype(result)
        # Result should vary
        assert not all(result == base_time)
        # Mean should be close to base time
        mean_delta = (result - base_time).mean().total_seconds() / 60
        assert -10 < mean_delta < 10  # Within 10 minutes of base

    def test_modify_time_jitter_with_series(self):
        """Test time jitter with different timestamps."""
        rng = np.random.default_rng(42)

        timestamps = pd.date_range("2024-01-01", periods=10, freq="H")
        result = modify_time_jitter(timestamps.values, rng, std_minutes=5.0)

        # All timestamps should be different from originals
        result_series = pd.Series(result)
        original_series = pd.Series(timestamps)
        assert not result_series.equals(original_series)


class TestCategoricalModifiers:
    """Tests for map_values modifier."""

    def test_modify_map_values_complete(self):
        """Test map_values with complete mapping."""
        values = np.array(["A", "B", "C", "A", "B"])
        mapping = {"A": "X", "B": "Y", "C": "Z"}
        result = modify_map_values(values, mapping)

        expected = np.array(["X", "Y", "Z", "X", "Y"])
        assert np.array_equal(result, expected)

    def test_modify_map_values_partial(self):
        """Test map_values with partial mapping."""
        values = np.array(["A", "B", "C", "D"])
        mapping = {"A": "X", "C": "Z"}
        result = modify_map_values(values, mapping)

        # A and C should be mapped, B and D unchanged
        assert result[0] == "X"
        assert result[1] == "B"  # Unchanged
        assert result[2] == "Z"
        assert result[3] == "D"  # Unchanged

    def test_modify_map_values_numeric(self):
        """Test map_values with numeric values."""
        values = np.array([1, 2, 3, 1, 2])
        mapping = {1: 10, 2: 20, 3: 30}
        result = modify_map_values(values, mapping)

        expected = np.array([10, 20, 30, 10, 20])
        assert np.array_equal(result, expected)


class TestTemporalModifiers:
    """Tests for seasonality modifier."""

    def test_modify_seasonality_hour(self):
        """Test seasonality modifier with hour dimension."""
        # Create timestamps at different hours
        timestamps = pd.date_range("2024-01-01 00:00", periods=24, freq="H")
        values = np.full(24, 100.0)

        # Define hourly weights (24 hours)
        weights = [0.5] * 6 + [1.0] * 12 + [0.8] * 6  # Lower at night

        result = modify_seasonality(values, timestamps, "hour", weights)

        # Midnight hours should have lower values (multiplied by 0.5)
        assert result[0] == pytest.approx(50.0, rel=0.01)
        # Noon hours should have normal values (multiplied by 1.0)
        assert result[12] == pytest.approx(100.0, rel=0.01)

    def test_modify_seasonality_dow(self):
        """Test seasonality modifier with day of week dimension."""
        # Create timestamps for 7 days
        timestamps = pd.date_range("2024-01-01", periods=7, freq="D")
        values = np.full(7, 100.0)

        # Define weekday weights (Mon-Sun)
        # Assume 2024-01-01 is Monday
        weights = [1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 1.5]  # Higher on weekends

        result = modify_seasonality(values, timestamps, "dow", weights)

        # Weekdays should have normal values
        assert result[0] == pytest.approx(100.0, rel=0.01)
        # Weekends should have higher values (multiplied by 1.5)
        assert result[5] == pytest.approx(150.0, rel=0.01)
        assert result[6] == pytest.approx(150.0, rel=0.01)

    def test_modify_seasonality_month(self):
        """Test seasonality modifier with month dimension."""
        # Create timestamps for 12 months
        timestamps = pd.date_range("2024-01-01", periods=12, freq="MS")
        values = np.full(12, 100.0)

        # Define monthly weights (12 months)
        weights = [0.8, 0.8, 1.0, 1.0, 1.2, 1.5, 1.5, 1.2, 1.0, 1.0, 1.2, 1.5]

        result = modify_seasonality(values, timestamps, "month", weights)

        # January should have lower values (0.8)
        assert result[0] == pytest.approx(80.0, rel=0.01)
        # June should have higher values (1.5)
        assert result[5] == pytest.approx(150.0, rel=0.01)
        # December should have higher values (1.5)
        assert result[11] == pytest.approx(150.0, rel=0.01)


class TestOutlierModifiers:
    """Tests for outliers modifier."""

    def test_modify_outliers_spike(self):
        """Test outliers modifier in spike mode."""
        rng = np.random.default_rng(42)
        values = np.full(100, 100.0)

        result = modify_outliers(
            values,
            rng,
            rate=0.1,  # 10% outliers
            mode="spike",
            magnitude_dist={
                "type": "uniform",
                "params": {"low": 1.0, "high": 3.0},
                "clamp": [1.0, 3.0]
            }
        )

        # About 10 values should be higher
        high_values = result > 105  # Allow some tolerance
        assert 5 <= high_values.sum() <= 15  # Approximately 10%

        # Max should be significantly higher
        assert result.max() > 200

    def test_modify_outliers_drop(self):
        """Test outliers modifier in drop mode."""
        rng = np.random.default_rng(42)
        values = np.full(100, 100.0)

        result = modify_outliers(
            values,
            rng,
            rate=0.05,  # 5% outliers
            mode="drop",
            magnitude_dist={
                "type": "uniform",
                "params": {"low": 2.0, "high": 5.0},
                "clamp": [2.0, 5.0]
            }
        )

        # About 5 values should be lower
        low_values = result < 95  # Allow some tolerance
        assert 2 <= low_values.sum() <= 8  # Approximately 5%

        # Min should be significantly lower
        assert result.min() < 50

    def test_modify_outliers_zero_rate(self):
        """Test outliers modifier with zero rate (no outliers)."""
        rng = np.random.default_rng(42)
        values = np.full(100, 100.0)

        result = modify_outliers(
            values,
            rng,
            rate=0.0,
            mode="spike",
            magnitude_dist={"type": "uniform", "params": {"low": 1.0, "high": 3.0}}
        )

        # All values should be unchanged
        assert np.allclose(result, values)

    def test_modify_outliers_invalid_mode(self):
        """Test that invalid outlier mode raises error."""
        rng = np.random.default_rng(42)
        values = np.full(100, 100.0)

        with pytest.raises(ValueError, match="Unknown outlier mode"):
            modify_outliers(
                values,
                rng,
                rate=0.1,
                mode="invalid",
                magnitude_dist={"type": "uniform", "params": {"low": 1.0, "high": 3.0}}
            )


class TestApplyModifiersIntegration:
    """Integration tests for apply_modifiers with multiple modifier chains."""

    def test_multiply_then_add(self):
        """Test chaining multiply and add modifiers."""
        rng = np.random.default_rng(42)
        values = np.array([10.0, 20.0, 30.0])

        modifiers = [
            {"transform": "multiply", "args": {"factor": 2.0}},
            {"transform": "add", "args": {"value": 5.0}}
        ]

        result = apply_modifiers(values, modifiers, rng, None)

        # (10 * 2) + 5 = 25
        # (20 * 2) + 5 = 45
        # (30 * 2) + 5 = 65
        expected = np.array([25.0, 45.0, 65.0])
        assert np.allclose(result, expected)

    def test_multiply_then_clamp(self):
        """Test chaining multiply and clamp modifiers."""
        rng = np.random.default_rng(42)
        values = np.array([10.0, 50.0, 100.0])

        modifiers = [
            {"transform": "multiply", "args": {"factor": 2.0}},
            {"transform": "clamp", "args": {"min": 30.0, "max": 150.0}}
        ]

        result = apply_modifiers(values, modifiers, rng, None)

        # 10 * 2 = 20, clamped to 30
        # 50 * 2 = 100, unchanged
        # 100 * 2 = 200, clamped to 150
        expected = np.array([30.0, 100.0, 150.0])
        assert np.allclose(result, expected)

    def test_add_jitter_then_clamp(self):
        """Test chaining add, jitter, and clamp modifiers."""
        rng = np.random.default_rng(42)
        values = np.array([100.0, 100.0, 100.0])

        modifiers = [
            {"transform": "add", "args": {"value": 50.0}},
            {"transform": "jitter", "args": {"std": 5.0, "mode": "add"}},
            {"transform": "clamp", "args": {"min": 140.0, "max": 160.0}}
        ]

        result = apply_modifiers(values, modifiers, rng, None)

        # All values should be in range [140, 160]
        assert all(result >= 140.0)
        assert all(result <= 160.0)

    def test_seasonality_with_context(self):
        """Test seasonality modifier with context DataFrame."""
        rng = np.random.default_rng(42)

        timestamps = pd.date_range("2024-01-01", periods=7, freq="D")
        values = np.full(7, 100.0)

        # Create context with timestamps
        context = pd.DataFrame({"order_time": timestamps})

        modifiers = [
            {
                "transform": "seasonality",
                "args": {
                    "dimension": "dow",
                    "weights": [1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 1.5]
                }
            }
        ]

        result = apply_modifiers(values, modifiers, rng, context)

        # Weekends should have higher values
        assert result[5] > 140
        assert result[6] > 140

    def test_map_values_then_multiply(self):
        """Test chaining map_values and multiply modifiers."""
        rng = np.random.default_rng(42)
        # Start with numeric codes that will be remapped
        values = np.array([1, 2, 3, 1], dtype=float)

        # First map to different values, then multiply
        modifiers = [
            {"transform": "map_values", "args": {"mapping": {1.0: 10.0, 2.0: 20.0, 3.0: 30.0}}},
            {"transform": "multiply", "args": {"factor": 1.5}}
        ]

        result = apply_modifiers(values, modifiers, rng, None)

        # 1 -> 10 -> 15
        # 2 -> 20 -> 30
        # 3 -> 30 -> 45
        expected = np.array([15.0, 30.0, 45.0, 15.0])
        assert np.allclose(result, expected)

    def test_unknown_modifier_skipped(self):
        """Test that unknown modifiers are skipped with warning."""
        rng = np.random.default_rng(42)
        values = np.array([10.0, 20.0, 30.0])

        modifiers = [
            {"transform": "multiply", "args": {"factor": 2.0}},
            {"transform": "unknown_modifier", "args": {}},  # Should be skipped
            {"transform": "add", "args": {"value": 5.0}}
        ]

        result = apply_modifiers(values, modifiers, rng, None)

        # Unknown modifier should be skipped
        # Result: (10 * 2) + 5 = 25
        expected = np.array([25.0, 45.0, 65.0])
        assert np.allclose(result, expected)

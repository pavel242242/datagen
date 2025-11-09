"""Tests for modifier functions."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from datagen.core.modifiers import modify_trend, apply_modifiers


class TestTrendModifier:
    """Tests for the trend modifier."""

    def test_exponential_growth(self):
        """Test exponential trend with 10% annual growth."""
        # Create timestamps spanning 2 years
        start = pd.Timestamp("2023-01-01")
        dates = pd.date_range(start, periods=8, freq="QE")  # Quarterly for 2 years

        # Base values all 100
        values = np.full(8, 100.0)

        # Apply 10% exponential growth
        result = modify_trend(
            values,
            pd.Series(dates),
            trend_type="exponential",
            growth_rate=0.10
        )

        # After 0 years: 100 * 1.1^0 = 100
        assert np.isclose(result[0], 100.0, rtol=0.01)

        # After ~2 years: 100 * 1.1^2 = 121
        # (index 7 is at 1.75 years, so 100 * 1.1^1.75 ≈ 118.6)
        assert result.iloc[-1] > 115 and result.iloc[-1] < 125

        # Should be monotonically increasing
        result_arr = result.values
        assert all(result_arr[i] < result_arr[i+1] for i in range(len(result_arr)-1))

    def test_linear_growth(self):
        """Test linear trend with 10% annual growth."""
        start = pd.Timestamp("2024-01-01")
        dates = pd.date_range(start, periods=4, freq="YE")  # 0, 1, 2, 3 years

        values = np.full(4, 100.0)

        result = modify_trend(
            values,
            pd.Series(dates),
            trend_type="linear",
            growth_rate=0.10
        )

        # After 0 years: 100 * (1 + 0.1*0) = 100
        assert np.isclose(result.iloc[0], 100.0, rtol=0.01)

        # After 1 year: 100 * (1 + 0.1*1) = 110
        assert np.isclose(result.iloc[1], 110.0, rtol=0.05)

        # After 2 years: 100 * (1 + 0.1*2) = 120
        assert np.isclose(result.iloc[2], 120.0, rtol=0.05)

        # After 3 years: 100 * (1 + 0.1*3) = 130
        assert np.isclose(result.iloc[3], 130.0, rtol=0.05)

    def test_logarithmic_growth(self):
        """Test logarithmic trend."""
        start = pd.Timestamp("2024-01-01")
        dates = pd.date_range(start, periods=10, freq="YE")

        values = np.full(10, 100.0)

        result = modify_trend(
            values,
            pd.Series(dates),
            trend_type="logarithmic",
            params={"a": 0.2, "b": 1.0}
        )

        # Should start at 100
        assert np.isclose(result.iloc[0], 100.0, rtol=0.01)

        # Should be increasing but with diminishing returns
        result_arr = result.values
        assert all(result_arr[i] < result_arr[i+1] for i in range(len(result_arr)-1))

        # Growth rate should slow down (second derivative negative)
        # Compare growth from year 0-1 vs year 8-9
        early_growth = result.iloc[1] - result.iloc[0]
        late_growth = result.iloc[9] - result.iloc[8]
        assert early_growth > late_growth

    def test_negative_growth_exponential(self):
        """Test exponential decay (negative growth)."""
        start = pd.Timestamp("2024-01-01")
        dates = pd.date_range(start, periods=5, freq="YE")

        values = np.full(5, 100.0)

        # -10% annual decline
        result = modify_trend(
            values,
            pd.Series(dates),
            trend_type="exponential",
            growth_rate=-0.10
        )

        # Should start at 100
        assert np.isclose(result.iloc[0], 100.0, rtol=0.01)

        # Should be decreasing
        result_arr = result.values
        assert all(result_arr[i] > result_arr[i+1] for i in range(len(result_arr)-1))

        # After 1 year: 100 * 0.9^1 = 90
        assert np.isclose(result.iloc[1], 90.0, rtol=0.05)

    def test_trend_with_apply_modifiers(self):
        """Test trend modifier through apply_modifiers interface."""
        start = pd.Timestamp("2024-01-01")
        dates = pd.date_range(start, periods=12, freq="ME")

        # Create context DataFrame with timestamp column
        context = pd.DataFrame({"order_time": dates})

        values = np.full(12, 50.0)

        modifiers = [
            {
                "transform": "trend",
                "args": {
                    "type": "exponential",
                    "growth_rate": 0.12,
                    "time_reference": "order_time"
                }
            }
        ]

        rng = np.random.default_rng(42)
        result = apply_modifiers(values, modifiers, rng, context)

        # Should have growth applied
        assert result[0] < result.iloc[-1]
        assert result[0] == pytest.approx(50.0, rel=0.01)

    def test_invalid_trend_type(self):
        """Test that invalid trend type raises error."""
        dates = pd.date_range("2024-01-01", periods=5, freq="ME")
        values = np.full(5, 100.0)

        with pytest.raises(ValueError, match="Unknown trend type"):
            modify_trend(values, pd.Series(dates), trend_type="invalid")

    def test_missing_growth_rate_exponential(self):
        """Test that exponential trend without growth_rate raises error."""
        dates = pd.date_range("2024-01-01", periods=5, freq="ME")
        values = np.full(5, 100.0)

        with pytest.raises(ValueError, match="requires growth_rate"):
            modify_trend(values, pd.Series(dates), trend_type="exponential")

    def test_missing_growth_rate_linear(self):
        """Test that linear trend without growth_rate raises error."""
        dates = pd.date_range("2024-01-01", periods=5, freq="ME")
        values = np.full(5, 100.0)

        with pytest.raises(ValueError, match="requires growth_rate"):
            modify_trend(values, pd.Series(dates), trend_type="linear")

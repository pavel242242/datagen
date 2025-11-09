"""Tests for Feature #1: Entity Vintage Effects.

Tests age calculation, curve evaluation, and vintage multiplier application.
"""

import pytest
import pandas as pd
import numpy as np

from datagen.core.vintage_utils import (
    calculate_entity_ages,
    evaluate_curve,
    apply_vintage_multipliers_to_fanout,
    apply_vintage_multipliers_to_values,
    _evaluate_array_curve,
    _evaluate_parametric_curve,
)


class TestAgeCalculation:
    """Test entity age calculation."""

    def test_calculate_ages_in_days(self):
        """Test age calculation in days."""
        entity_created = pd.to_datetime(["2024-01-01", "2024-01-15", "2024-02-01"])
        reference_time = pd.to_datetime(["2024-02-01", "2024-02-01", "2024-02-01"])

        ages = calculate_entity_ages(entity_created, reference_time, "day")

        assert ages[0] == 31  # 31 days old
        assert ages[1] == 17  # 17 days old
        assert ages[2] == 0  # 0 days old (same day)

    def test_calculate_ages_in_months(self):
        """Test age calculation in months (approximate)."""
        entity_created = pd.to_datetime(["2024-01-01", "2024-02-01"])
        reference_time = pd.to_datetime(["2024-03-01", "2024-04-01"])

        ages = calculate_entity_ages(entity_created, reference_time, "month")

        assert np.isclose(ages[0], 2.0, atol=0.1)  # ~2 months
        assert np.isclose(ages[1], 2.0, atol=0.1)  # ~2 months

    def test_calculate_ages_in_years(self):
        """Test age calculation in years."""
        entity_created = pd.to_datetime(["2023-01-01", "2023-07-01"])
        reference_time = pd.to_datetime(["2024-01-01", "2024-07-01"])

        ages = calculate_entity_ages(entity_created, reference_time, "year")

        assert np.isclose(ages[0], 1.0, atol=0.01)  # 1 year
        assert np.isclose(ages[1], 1.0, atol=0.01)  # 1 year

    def test_negative_ages_clamped_to_zero(self):
        """Test that future created_at dates result in zero age."""
        entity_created = pd.to_datetime(["2024-03-01"])
        reference_time = pd.to_datetime(["2024-01-01"])  # Before created

        ages = calculate_entity_ages(entity_created, reference_time, "day")

        assert ages[0] == 0  # Can't use entity before it's created


class TestArrayCurveEvaluation:
    """Test array-based curve evaluation."""

    def test_array_curve_exact_bins(self):
        """Test array curve with exact age bins."""
        ages = np.array([0, 1, 2, 3])
        curve = [1.0, 0.75, 0.6, 0.5]

        multipliers = _evaluate_array_curve(ages, curve)

        assert np.allclose(multipliers, [1.0, 0.75, 0.6, 0.5])

    def test_array_curve_beyond_array(self):
        """Test array curve with ages beyond array length."""
        ages = np.array([0, 1, 2, 5, 10])
        curve = [1.0, 0.75, 0.6, 0.5]

        multipliers = _evaluate_array_curve(ages, curve)

        # Ages beyond array use last value
        assert multipliers[0] == 1.0
        assert multipliers[1] == 0.75
        assert multipliers[2] == 0.6
        assert multipliers[3] == 0.5  # Age 5 → last value
        assert multipliers[4] == 0.5  # Age 10 → last value

    def test_array_curve_float_ages_rounded(self):
        """Test array curve with float ages (should round)."""
        ages = np.array([0.2, 0.8, 1.4, 1.6, 2.9])
        curve = [1.0, 0.75, 0.6, 0.5]

        multipliers = _evaluate_array_curve(ages, curve)

        # 0.2 → 0, 0.8 → 1, 1.4 → 1, 1.6 → 2, 2.9 → 3
        assert multipliers[0] == 1.0
        assert multipliers[1] == 0.75
        assert multipliers[2] == 0.75
        assert multipliers[3] == 0.6
        assert multipliers[4] == 0.5

    def test_array_curve_empty_raises_error(self):
        """Test that empty curve raises error."""
        ages = np.array([0, 1, 2])

        with pytest.raises(ValueError, match="cannot be empty"):
            _evaluate_array_curve(ages, [])


class TestParametricCurveEvaluation:
    """Test parametric curve evaluation."""

    def test_logarithmic_curve(self):
        """Test logarithmic curve: multiplier = a + b * log(age + 1)."""
        ages = np.array([0, 1, 2, 5, 10])
        spec = {"curve_type": "logarithmic", "params": {"a": 1.0, "b": -0.15}}

        multipliers = _evaluate_parametric_curve(ages, spec)

        # multiplier = 1.0 + (-0.15) * log(age + 1)
        expected = 1.0 + (-0.15) * np.log(ages + 1)
        assert np.allclose(multipliers, expected)

        # Age 0: 1.0 + (-0.15) * log(1) = 1.0
        # Age 1: 1.0 + (-0.15) * log(2) ≈ 0.896
        assert np.isclose(multipliers[0], 1.0)
        assert np.isclose(multipliers[1], 0.896, atol=0.01)

    def test_exponential_curve(self):
        """Test exponential curve: multiplier = a * exp(b * age)."""
        ages = np.array([0, 1, 2])
        spec = {"curve_type": "exponential", "params": {"a": 1.0, "b": -0.2}}

        multipliers = _evaluate_parametric_curve(ages, spec)

        # multiplier = 1.0 * exp(-0.2 * age)
        expected = 1.0 * np.exp(-0.2 * ages)
        assert np.allclose(multipliers, expected)

        # Age 0: 1.0 * exp(0) = 1.0
        # Age 1: 1.0 * exp(-0.2) ≈ 0.819
        assert np.isclose(multipliers[0], 1.0)
        assert np.isclose(multipliers[1], 0.819, atol=0.01)

    def test_linear_curve(self):
        """Test linear curve: multiplier = a + b * age."""
        ages = np.array([0, 1, 2, 5])
        spec = {"curve_type": "linear", "params": {"a": 1.0, "b": -0.1}}

        multipliers = _evaluate_parametric_curve(ages, spec)

        # multiplier = 1.0 + (-0.1) * age
        expected = 1.0 + (-0.1) * ages
        assert np.allclose(multipliers, expected)

        # Age 0: 1.0
        # Age 1: 0.9
        # Age 5: 0.5
        assert multipliers[0] == 1.0
        assert multipliers[1] == 0.9
        assert multipliers[3] == 0.5  # Index 3 corresponds to age 5

    def test_negative_multipliers_clamped_to_zero(self):
        """Test that negative multipliers are clamped to zero."""
        ages = np.array([0, 5, 10, 20])
        spec = {"curve_type": "linear", "params": {"a": 1.0, "b": -0.2}}

        multipliers = _evaluate_parametric_curve(ages, spec)

        # multiplier = 1.0 + (-0.2) * age
        # Age 0: 1.0
        # Age 5: 0.0
        # Age 10: -1.0 → clamped to 0
        # Age 20: -3.0 → clamped to 0
        assert multipliers[0] == 1.0
        assert multipliers[1] == 0.0
        assert multipliers[2] == 0.0
        assert multipliers[3] == 0.0

    def test_unknown_curve_type_raises_error(self):
        """Test that unknown curve type raises error."""
        ages = np.array([0, 1, 2])
        spec = {"curve_type": "polynomial", "params": {"a": 1.0, "b": -0.1}}

        with pytest.raises(ValueError, match="Unknown curve_type"):
            _evaluate_parametric_curve(ages, spec)

    def test_missing_params_raises_error(self):
        """Test that missing params raises error."""
        ages = np.array([0, 1, 2])
        spec = {"curve_type": "logarithmic", "params": {"a": 1.0}}  # Missing 'b'

        with pytest.raises(ValueError, match="must include 'a' and 'b'"):
            _evaluate_parametric_curve(ages, spec)


class TestEvaluateCurve:
    """Test unified evaluate_curve function."""

    def test_evaluate_array_curve(self):
        """Test evaluate_curve with array-based curve."""
        ages = np.array([0, 1, 2])
        curve = [1.0, 0.75, 0.6]

        multipliers = evaluate_curve(ages, curve)

        assert np.allclose(multipliers, [1.0, 0.75, 0.6])

    def test_evaluate_parametric_curve(self):
        """Test evaluate_curve with parametric curve."""
        ages = np.array([0, 1, 2])
        curve = {"curve_type": "logarithmic", "params": {"a": 1.0, "b": -0.1}}

        multipliers = evaluate_curve(ages, curve)

        expected = 1.0 + (-0.1) * np.log(ages + 1)
        assert np.allclose(multipliers, expected)

    def test_invalid_curve_type_raises_error(self):
        """Test that invalid curve type raises error."""
        ages = np.array([0, 1, 2])

        with pytest.raises(ValueError, match="Invalid curve_spec type"):
            evaluate_curve(ages, "invalid")


class TestFanoutMultipliers:
    """Test vintage multipliers on fanout."""

    def test_fanout_multipliers_array_curve(self):
        """Test fanout multipliers with array-based activity decay."""
        fanout_counts = np.array([10, 10, 10, 10])
        entity_ages = np.array([0, 1, 2, 3])

        vintage_config = {
            "age_based_multipliers": {
                "activity_decay": {
                    "curve": [1.0, 0.75, 0.6, 0.5],
                    "time_unit": "month",
                    "applies_to": "fanout",
                }
            }
        }

        result = apply_vintage_multipliers_to_fanout(fanout_counts, entity_ages, vintage_config)

        # 10 * [1.0, 0.75, 0.6, 0.5] = [10, 7.5, 6, 5] → rounded to int
        assert result[0] == 10
        assert result[1] == 8  # 7.5 rounded to 8
        assert result[2] == 6
        assert result[3] == 5

    def test_fanout_multipliers_logarithmic_curve(self):
        """Test fanout multipliers with logarithmic decay."""
        fanout_counts = np.array([100, 100, 100])
        entity_ages = np.array([0, 6, 12])

        vintage_config = {
            "age_based_multipliers": {
                "retention_curve": {
                    "curve": {"curve_type": "logarithmic", "params": {"a": 1.0, "b": -0.15}},
                    "time_unit": "month",
                    "applies_to": "fanout",
                }
            }
        }

        result = apply_vintage_multipliers_to_fanout(fanout_counts, entity_ages, vintage_config)

        # multiplier = 1.0 + (-0.15) * log(age + 1)
        # Age 0: 1.0 → 100
        # Age 6: 1.0 - 0.15*log(7) ≈ 0.708 → 71
        # Age 12: 1.0 - 0.15*log(13) ≈ 0.615 → 62
        assert result[0] == 100
        assert 70 <= result[1] <= 72
        assert 61 <= result[2] <= 63

    def test_fanout_no_vintage_config(self):
        """Test that fanout is unchanged with no vintage config."""
        fanout_counts = np.array([10, 20, 30])
        entity_ages = np.array([0, 1, 2])

        result = apply_vintage_multipliers_to_fanout(fanout_counts, entity_ages, None)

        assert np.array_equal(result, fanout_counts)

    def test_fanout_non_fanout_multipliers_ignored(self):
        """Test that multipliers not applying to fanout are ignored."""
        fanout_counts = np.array([10, 10, 10])
        entity_ages = np.array([0, 1, 2])

        vintage_config = {
            "age_based_multipliers": {
                "value_growth": {
                    "curve": [1.0, 2.0, 3.0],
                    "time_unit": "month",
                    "applies_to": ["amount"],  # Not fanout
                }
            }
        }

        result = apply_vintage_multipliers_to_fanout(fanout_counts, entity_ages, vintage_config)

        # Should be unchanged
        assert np.array_equal(result, fanout_counts)


class TestValueMultipliers:
    """Test vintage multipliers on column values."""

    def test_value_multipliers_specific_column(self):
        """Test value multipliers applied to specific column."""
        values = np.array([100.0, 100.0, 100.0])
        entity_ages = np.array([0, 1, 2])

        vintage_config = {
            "age_based_multipliers": {
                "value_growth": {
                    "curve": [1.0, 1.5, 2.0],
                    "time_unit": "month",
                    "applies_to": ["amount"],
                }
            }
        }

        result = apply_vintage_multipliers_to_values(values, entity_ages, "amount", vintage_config)

        # 100 * [1.0, 1.5, 2.0] = [100, 150, 200]
        assert np.allclose(result, [100, 150, 200])

    def test_value_multipliers_all_columns(self):
        """Test value multipliers applied to all columns."""
        values = np.array([100.0, 100.0, 100.0])
        entity_ages = np.array([0, 1, 2])

        vintage_config = {
            "age_based_multipliers": {
                "value_growth": {
                    "curve": [1.0, 1.2, 1.4],
                    "time_unit": "month",
                    "applies_to": "all",
                }
            }
        }

        result = apply_vintage_multipliers_to_values(
            values, entity_ages, "any_column", vintage_config
        )

        assert np.allclose(result, [100, 120, 140])

    def test_value_multipliers_column_not_in_list(self):
        """Test that multipliers for other columns are not applied."""
        values = np.array([100.0, 100.0, 100.0])
        entity_ages = np.array([0, 1, 2])

        vintage_config = {
            "age_based_multipliers": {
                "value_growth": {
                    "curve": [1.0, 2.0, 3.0],
                    "time_unit": "month",
                    "applies_to": ["amount", "quantity"],
                }
            }
        }

        result = apply_vintage_multipliers_to_values(values, entity_ages, "price", vintage_config)

        # Should be unchanged
        assert np.array_equal(result, values)

    def test_value_multipliers_fanout_ignored(self):
        """Test that fanout multipliers are ignored for values."""
        values = np.array([100.0, 100.0, 100.0])
        entity_ages = np.array([0, 1, 2])

        vintage_config = {
            "age_based_multipliers": {
                "activity_decay": {
                    "curve": [1.0, 0.5, 0.25],
                    "time_unit": "month",
                    "applies_to": "fanout",  # Should be ignored
                }
            }
        }

        result = apply_vintage_multipliers_to_values(values, entity_ages, "amount", vintage_config)

        # Should be unchanged
        assert np.array_equal(result, values)

    def test_value_multipliers_parametric_curve(self):
        """Test value multipliers with parametric curve."""
        values = np.array([1000.0, 1000.0, 1000.0])
        entity_ages = np.array([0, 6, 12])

        vintage_config = {
            "age_based_multipliers": {
                "ltv_growth": {
                    "curve": {
                        "curve_type": "logarithmic",
                        "params": {"a": 1.0, "b": 0.2},  # Growth, not decay
                    },
                    "time_unit": "month",
                    "applies_to": "all",
                }
            }
        }

        result = apply_vintage_multipliers_to_values(values, entity_ages, "ltv", vintage_config)

        # multiplier = 1.0 + 0.2 * log(age + 1)
        # Age 0: 1.0 → 1000
        # Age 6: 1.0 + 0.2*log(7) ≈ 1.389 → 1389
        # Age 12: 1.0 + 0.2*log(13) ≈ 1.513 → 1513
        assert result[0] == 1000
        assert 1380 <= result[1] <= 1400
        assert 1510 <= result[2] <= 1520


# Integration test would go here - test end-to-end with executor
# This will be added in a separate test file or integration test suite

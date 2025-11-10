"""
Tests for Feature #6: Diffusion and Adoption Curves
"""

import pytest
import numpy as np
import pandas as pd
from src.datagen.core.generators.diffusion import (
    generate_diffusion_timestamps,
    assign_adopter_categories,
    generate_viral_adoption
)


class TestDiffusionTimestamps:
    """Test diffusion curve timestamp generation."""

    def test_logistic_curve_generates_s_shape(self):
        """Logistic curve should generate S-shaped distribution."""
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-12-31")

        timestamps = generate_diffusion_timestamps(
            n_rows=1000,
            start_time=start,
            end_time=end,
            curve_type="logistic",
            inflection_point=0.5,
            steepness=10.0,
            rng=np.random.default_rng(42)
        )

        assert len(timestamps) == 1000
        assert all(start <= t <= end for t in timestamps)

        # Check S-curve property: more timestamps near middle
        # Divide into early/middle/late thirds
        duration = (end - start).total_seconds()
        early_cutoff = start + pd.Timedelta(seconds=duration / 3)
        late_cutoff = start + pd.Timedelta(seconds=2 * duration / 3)

        early = sum(t < early_cutoff for t in timestamps)
        middle = sum(early_cutoff <= t < late_cutoff for t in timestamps)
        late = sum(t >= late_cutoff for t in timestamps)

        # Middle third should have most timestamps (S-curve peak)
        assert middle > early
        assert middle > late

    def test_exponential_curve_front_loaded(self):
        """Exponential curve should be front-loaded."""
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-12-31")

        timestamps = generate_diffusion_timestamps(
            n_rows=1000,
            start_time=start,
            end_time=end,
            curve_type="exponential",
            steepness=5.0,
            rng=np.random.default_rng(42)
        )

        assert len(timestamps) == 1000

        # Exponential should have more early adopters
        duration = (end - start).total_seconds()
        midpoint = start + pd.Timedelta(seconds=duration / 2)

        early_half = sum(t < midpoint for t in timestamps)
        late_half = sum(t >= midpoint for t in timestamps)

        assert early_half > late_half

    def test_linear_curve_uniform_distribution(self):
        """Linear curve should have uniform distribution."""
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-12-31")

        timestamps = generate_diffusion_timestamps(
            n_rows=1000,
            start_time=start,
            end_time=end,
            curve_type="linear",
            rng=np.random.default_rng(42)
        )

        assert len(timestamps) == 1000

        # Linear should be roughly uniform across quartiles
        duration = (end - start).total_seconds()
        q1 = start + pd.Timedelta(seconds=duration / 4)
        q2 = start + pd.Timedelta(seconds=duration / 2)
        q3 = start + pd.Timedelta(seconds=3 * duration / 4)

        count_q1 = sum(t < q1 for t in timestamps)
        count_q2 = sum(q1 <= t < q2 for t in timestamps)
        count_q3 = sum(q2 <= t < q3 for t in timestamps)
        count_q4 = sum(t >= q3 for t in timestamps)

        # Should be roughly 250 each (within 20% tolerance)
        assert 200 < count_q1 < 300
        assert 200 < count_q2 < 300
        assert 200 < count_q3 < 300
        assert 200 < count_q4 < 300

    def test_deterministic_with_seed(self):
        """Same seed should produce same timestamps."""
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-12-31")

        timestamps1 = generate_diffusion_timestamps(
            n_rows=100,
            start_time=start,
            end_time=end,
            curve_type="logistic",
            rng=np.random.default_rng(42)
        )

        timestamps2 = generate_diffusion_timestamps(
            n_rows=100,
            start_time=start,
            end_time=end,
            curve_type="logistic",
            rng=np.random.default_rng(42)
        )

        pd.testing.assert_series_equal(timestamps1, timestamps2)

    def test_inflection_point_shift(self):
        """Changing inflection point should shift S-curve peak."""
        start = pd.Timestamp("2024-01-01")
        end = pd.Timestamp("2024-12-31")
        duration = (end - start).total_seconds()

        # Early inflection (30%)
        timestamps_early = generate_diffusion_timestamps(
            n_rows=1000,
            start_time=start,
            end_time=end,
            curve_type="logistic",
            inflection_point=0.3,
            steepness=10.0,
            rng=np.random.default_rng(42)
        )

        # Late inflection (70%)
        timestamps_late = generate_diffusion_timestamps(
            n_rows=1000,
            start_time=start,
            end_time=end,
            curve_type="logistic",
            inflection_point=0.7,
            steepness=10.0,
            rng=np.random.default_rng(42)
        )

        # Median should shift
        median_early = timestamps_early.median()
        median_late = timestamps_late.median()

        assert median_late > median_early


class TestAdopterCategories:
    """Test Rogers adopter category assignment."""

    def test_default_rogers_distribution(self):
        """Default should use Rogers diffusion model."""
        categories = assign_adopter_categories(
            n_rows=10000,
            rng=np.random.default_rng(42)
        )

        counts = categories.value_counts(normalize=True)

        # Should be close to Rogers proportions
        assert 0.02 < counts["innovators"] < 0.03
        assert 0.12 < counts["early_adopters"] < 0.15
        assert 0.32 < counts["early_majority"] < 0.36
        assert 0.32 < counts["late_majority"] < 0.36
        assert 0.14 < counts["laggards"] < 0.18

    def test_custom_distribution(self):
        """Should accept custom distributions."""
        custom_dist = {
            "power_users": 0.1,
            "regular_users": 0.6,
            "occasional_users": 0.3
        }

        categories = assign_adopter_categories(
            n_rows=1000,
            distribution=custom_dist,
            rng=np.random.default_rng(42)
        )

        counts = categories.value_counts(normalize=True)

        # Should match custom distribution (within tolerance)
        assert 0.08 < counts["power_users"] < 0.12
        assert 0.57 < counts["regular_users"] < 0.63
        assert 0.27 < counts["occasional_users"] < 0.33

    def test_deterministic_with_seed(self):
        """Same seed should produce same assignments."""
        categories1 = assign_adopter_categories(
            n_rows=100,
            rng=np.random.default_rng(42)
        )

        categories2 = assign_adopter_categories(
            n_rows=100,
            rng=np.random.default_rng(42)
        )

        pd.testing.assert_series_equal(categories1, categories2)


class TestViralAdoption:
    """Test viral adoption dynamics."""

    def test_viral_growth_from_seeds(self):
        """Viral adoption should grow from seed adopters."""
        adopters = generate_viral_adoption(
            seed_adopters=10,
            viral_coefficient=1.5,
            population_size=1000,
            timesteps=50,
            rng=np.random.default_rng(42)
        )

        assert len(adopters) == 50
        assert adopters[0] == 10  # Starts with seeds
        assert adopters[-1] > 10  # Grows over time
        assert adopters[-1] <= 1000  # Caps at population

        # Should be monotonically increasing
        assert all(adopters[i] <= adopters[i + 1] for i in range(len(adopters) - 1))

    def test_viral_saturation(self):
        """Viral growth should saturate as population fills."""
        adopters = generate_viral_adoption(
            seed_adopters=100,
            viral_coefficient=2.0,  # High viral coefficient
            population_size=1000,
            timesteps=100,
            rng=np.random.default_rng(42)
        )

        # Should reach saturation
        assert adopters[-1] == 1000

        # Growth rate should slow as saturation approaches
        early_growth = adopters[10] - adopters[0]
        late_growth = adopters[-1] - adopters[-11]
        assert early_growth > late_growth

    def test_low_viral_coefficient_slow_growth(self):
        """Low viral coefficient should result in slower growth."""
        adopters_low = generate_viral_adoption(
            seed_adopters=10,
            viral_coefficient=0.3,  # Low
            population_size=10000,  # Larger population
            timesteps=30,  # Fewer timesteps
            rng=np.random.default_rng(42)
        )

        adopters_high = generate_viral_adoption(
            seed_adopters=10,
            viral_coefficient=1.5,  # High
            population_size=10000,  # Larger population
            timesteps=30,  # Fewer timesteps
            rng=np.random.default_rng(42)
        )

        # High coefficient should grow faster
        assert adopters_high[-1] > adopters_low[-1]

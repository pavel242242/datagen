"""Tests for Phase 2 generators."""

import numpy as np
import pandas as pd
import pytest

from datagen.core.generators.primitives import (
    generate_sequence,
    generate_choice,
    generate_distribution,
    generate_zipf_weights,
    sample_fanout,
)
from datagen.core.generators.temporal import (
    generate_datetime_series,
    get_seasonality_multiplier,
)
from datagen.core.generators.semantic import (
    generate_faker,
    resolve_locale,
)
from datagen.core.generators.registry import (
    GeneratorRegistry,
    LookupResolver,
    generate_expression,
)


# ============================================================================
# Primitives Tests
# ============================================================================

def test_generate_sequence():
    """Test sequence generator."""
    seq = generate_sequence(1, 1, 10)
    assert len(seq) == 10
    assert list(seq) == list(range(1, 11))

    seq2 = generate_sequence(100, 10, 5)
    assert list(seq2) == [100, 110, 120, 130, 140]


def test_generate_choice_uniform():
    """Test choice generator with uniform weights."""
    rng = np.random.default_rng(42)
    choices = ['a', 'b', 'c']
    result = generate_choice(choices, 100, rng)

    assert len(result) == 100
    assert all(v in choices for v in result)


def test_generate_choice_weighted():
    """Test choice generator with explicit weights."""
    rng = np.random.default_rng(42)
    choices = [1, 2, 3]
    weights = [0.8, 0.15, 0.05]  # Heavily favor 1

    result = generate_choice(choices, 1000, rng, weights=weights)

    # Count occurrences
    unique, counts = np.unique(result, return_counts=True)
    freqs = dict(zip(unique, counts / 1000))

    # 1 should be most common
    assert freqs[1] > 0.7  # Should be around 0.8


def test_generate_zipf_weights():
    """Test Zipf weight generation."""
    weights = generate_zipf_weights(10, alpha=1.5)

    assert len(weights) == 10
    assert np.isclose(weights.sum(), 1.0)
    # First weight should be largest
    assert weights[0] == max(weights)


def test_generate_distribution_normal():
    """Test normal distribution."""
    rng = np.random.default_rng(42)
    values = generate_distribution("normal", {"mean": 100, "std": 15}, 1000, rng, (50, 150))

    assert len(values) == 1000
    assert all(50 <= v <= 150 for v in values)
    assert 90 < values.mean() < 110  # Should be around 100


def test_generate_distribution_lognormal():
    """Test lognormal distribution."""
    rng = np.random.default_rng(42)
    values = generate_distribution("lognormal", {"mean": 3.0, "sigma": 0.5}, 1000, rng, (1, 1000))

    assert len(values) == 1000
    assert all(1 <= v <= 1000 for v in values)
    # Lognormal should be skewed
    assert values.mean() > np.median(values)


def test_generate_distribution_poisson():
    """Test Poisson distribution."""
    rng = np.random.default_rng(42)
    values = generate_distribution("poisson", {"lambda": 5.0}, 1000, rng, (0, 20))

    assert len(values) == 1000
    assert all(0 <= v <= 20 for v in values)
    assert 4 < values.mean() < 6  # Should be around 5


def test_sample_fanout_poisson():
    """Test Poisson fanout sampling."""
    rng = np.random.default_rng(42)
    counts = sample_fanout("poisson", 100, rng, lambda_=5, min_val=0, max_val=20)

    assert len(counts) == 100
    assert all(0 <= c <= 20 for c in counts)
    assert 4 < counts.mean() < 6


def test_sample_fanout_uniform():
    """Test uniform fanout sampling."""
    rng = np.random.default_rng(42)
    counts = sample_fanout("uniform", 100, rng, min_val=3, max_val=7)

    assert len(counts) == 100
    assert all(3 <= c <= 7 for c in counts)


# ============================================================================
# Temporal Tests
# ============================================================================

def test_generate_datetime_series():
    """Test datetime series generation."""
    rng = np.random.default_rng(42)
    series = generate_datetime_series(
        "2024-01-01T00:00:00Z",
        "2024-01-31T23:59:59Z",
        "D",
        10,
        rng
    )

    assert len(series) == 10
    start = pd.to_datetime("2024-01-01T00:00:00Z")
    end = pd.to_datetime("2024-02-01T00:00:00Z")
    assert all(start <= ts <= end for ts in series)


def test_generate_datetime_series_with_pattern():
    """Test datetime series with DOW pattern."""
    rng = np.random.default_rng(42)

    # Heavily favor Monday (index 0)
    dow_weights = [10.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

    series = generate_datetime_series(
        "2024-01-01T00:00:00Z",  # Monday
        "2024-01-31T23:59:59Z",
        "D",
        100,
        rng,
        pattern={"dimension": "dow", "weights": dow_weights}
    )

    # Count Mondays
    mondays = sum(1 for ts in series if ts.dayofweek == 0)

    # Should have significantly more Mondays than other days
    assert mondays > 50


def test_get_seasonality_multiplier():
    """Test seasonality multiplier calculation."""
    timestamps = pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03'])  # Mon, Tue, Wed

    # Monday=1.0, Tuesday=1.5, Wednesday=0.8
    mults = get_seasonality_multiplier(
        timestamps,
        "dow",
        [1.0, 1.5, 0.8, 1.0, 1.0, 1.0, 1.0]
    )

    assert len(mults) == 3
    assert mults[0] == 1.0
    assert mults[1] == 1.5
    assert mults[2] == 0.8


# ============================================================================
# Semantic Tests
# ============================================================================

def test_resolve_locale():
    """Test locale resolution."""
    assert resolve_locale("US") == "en_US"
    assert resolve_locale("DE") == "de_DE"
    assert resolve_locale("Prague") == "cs_CZ"
    assert resolve_locale("Unknown") == "en_US"  # Fallback


def test_generate_faker_basic():
    """Test Faker generation."""
    rng = np.random.default_rng(42)
    names = generate_faker("name", 5, rng)

    assert len(names) == 5
    assert all(isinstance(n, str) and len(n) > 0 for n in names)


def test_generate_faker_with_locale():
    """Test Faker with specific locale."""
    rng = np.random.default_rng(42)
    names_us = generate_faker("name", 3, rng, locale="en_US")
    names_de = generate_faker("name", 3, rng, locale="de_DE")

    # Both should work (actual names will differ due to locale)
    assert len(names_us) == 3
    assert len(names_de) == 3


def test_generate_faker_locale_from_values():
    """Test Faker with locale derived from values."""
    rng = np.random.default_rng(42)
    countries = np.array(["US", "DE", "FR"])

    names = generate_faker("name", 3, rng, locale_from_values=countries)

    assert len(names) == 3


# ============================================================================
# Registry Tests
# ============================================================================

def test_lookup_resolver():
    """Test lookup resolver."""
    resolver = LookupResolver()

    # Register a table
    df = pd.DataFrame({"user_id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]})
    resolver.register_table("user", df)

    # Lookup random values
    rng = np.random.default_rng(42)
    user_ids = resolver.lookup("user.user_id", 10, rng)

    assert len(user_ids) == 10
    assert all(uid in [1, 2, 3] for uid in user_ids)


def test_lookup_resolver_with_join():
    """Test lookup with join condition."""
    resolver = LookupResolver()

    # Register tables
    products = pd.DataFrame({
        "product_id": [101, 102, 103],
        "name": ["Widget", "Gadget", "Gizmo"]
    })
    resolver.register_table("product", products)

    # Parent data referencing products
    parent = pd.DataFrame({"product_id": [101, 102, 101, 103]})

    rng = np.random.default_rng(42)
    names = resolver.lookup(
        "product.name",
        4,
        rng,
        on={"product_id": "product_id"},
        parent_data=parent
    )

    # Should match product_ids
    assert names[0] == "Widget"  # 101
    assert names[1] == "Gadget"  # 102
    assert names[2] == "Widget"  # 101
    assert names[3] == "Gizmo"   # 103


def test_generate_expression():
    """Test expression evaluation."""
    df = pd.DataFrame({"quantity": [2, 3, 5], "price": [10.0, 20.0, 15.0]})

    result = generate_expression("quantity * price", df)

    assert len(result) == 3
    assert result[0] == 20.0
    assert result[1] == 60.0
    assert result[2] == 75.0


def test_generator_registry_sequence():
    """Test registry with sequence generator."""
    registry = GeneratorRegistry()
    rng = np.random.default_rng(42)

    spec = {"sequence": {"start": 1, "step": 1}}
    result = registry.generate(spec, 5, rng)

    assert list(result) == [1, 2, 3, 4, 5]


def test_generator_registry_choice():
    """Test registry with choice generator."""
    registry = GeneratorRegistry()
    rng = np.random.default_rng(42)

    spec = {"choice": {"choices": ["a", "b", "c"]}}
    result = registry.generate(spec, 10, rng)

    assert len(result) == 10
    assert all(v in ["a", "b", "c"] for v in result)


def test_generator_registry_distribution():
    """Test registry with distribution generator."""
    registry = GeneratorRegistry()
    rng = np.random.default_rng(42)

    spec = {
        "distribution": {
            "type": "normal",
            "params": {"mean": 50, "std": 10},
            "clamp": [0, 100]
        }
    }
    result = registry.generate(spec, 100, rng)

    assert len(result) == 100
    assert all(0 <= v <= 100 for v in result)


def test_generator_registry_datetime():
    """Test registry with datetime generator."""
    registry = GeneratorRegistry()
    rng = np.random.default_rng(42)

    spec = {
        "datetime_series": {
            "within": "timeframe",
            "freq": "D"
        }
    }
    timeframe = {"start": "2024-01-01T00:00:00Z", "end": "2024-01-31T23:59:59Z"}

    result = registry.generate(spec, 10, rng, timeframe=timeframe)

    assert len(result) == 10


def test_generator_registry_faker():
    """Test registry with Faker generator."""
    registry = GeneratorRegistry()
    rng = np.random.default_rng(42)

    spec = {"faker": {"method": "email"}}
    result = registry.generate(spec, 5, rng)

    assert len(result) == 5
    assert all("@" in email for email in result)


def test_generator_registry_expression():
    """Test registry with expression generator."""
    registry = GeneratorRegistry()
    rng = np.random.default_rng(42)

    context = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
    spec = {"expression": {"code": "a + b"}}

    result = registry.generate(spec, 3, rng, context=context)

    assert list(result) == [11, 22, 33]

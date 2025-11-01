"""Tests for seed derivation."""

import numpy as np
from datagen.core.seed import derive_seed, get_rng, SeedManager


def test_derive_seed_deterministic():
    """Test that same inputs produce same seed."""
    seed1 = derive_seed(42, "user", "age")
    seed2 = derive_seed(42, "user", "age")
    assert seed1 == seed2


def test_derive_seed_different_inputs():
    """Test that different inputs produce different seeds."""
    seed1 = derive_seed(42, "user", "age")
    seed2 = derive_seed(42, "user", "name")
    seed3 = derive_seed(43, "user", "age")

    assert seed1 != seed2
    assert seed1 != seed3
    assert seed2 != seed3


def test_derive_seed_range():
    """Test that derived seeds are in valid numpy range."""
    for i in range(100):
        seed = derive_seed(i, "test", "column")
        assert 0 <= seed < 2**32


def test_get_rng_produces_generator():
    """Test that get_rng returns numpy Generator."""
    rng = get_rng(42, "user")
    assert isinstance(rng, np.random.Generator)


def test_get_rng_deterministic():
    """Test that same inputs produce same random sequence."""
    rng1 = get_rng(42, "user", "age")
    values1 = rng1.normal(0, 1, size=10)

    rng2 = get_rng(42, "user", "age")
    values2 = rng2.normal(0, 1, size=10)

    np.testing.assert_array_equal(values1, values2)


def test_seed_manager_node_seed():
    """Test SeedManager node-level seed derivation."""
    sm = SeedManager(master_seed=42)

    seed1 = sm.node_seed("user")
    seed2 = sm.node_seed("user")
    seed3 = sm.node_seed("order")

    assert seed1 == seed2
    assert seed1 != seed3


def test_seed_manager_column_seed():
    """Test SeedManager column-level seed derivation."""
    sm = SeedManager(master_seed=42)

    seed1 = sm.column_seed("user", "age")
    seed2 = sm.column_seed("user", "age")
    seed3 = sm.column_seed("user", "name")

    assert seed1 == seed2
    assert seed1 != seed3


def test_seed_manager_parent_seed():
    """Test SeedManager parent-based seed derivation."""
    sm = SeedManager(master_seed=42)

    seed1 = sm.parent_seed("order", "user_123")
    seed2 = sm.parent_seed("order", "user_123")
    seed3 = sm.parent_seed("order", "user_456")

    assert seed1 == seed2
    assert seed1 != seed3


def test_seed_manager_row_seed():
    """Test SeedManager row-level seed derivation."""
    sm = SeedManager(master_seed=42)

    seed1 = sm.row_seed("order", "user_123", 0)
    seed2 = sm.row_seed("order", "user_123", 0)
    seed3 = sm.row_seed("order", "user_123", 1)

    assert seed1 == seed2
    assert seed1 != seed3


def test_seed_manager_rng_methods():
    """Test that SeedManager RNG methods return Generators."""
    sm = SeedManager(master_seed=42)

    assert isinstance(sm.node_rng("user"), np.random.Generator)
    assert isinstance(sm.column_rng("user", "age"), np.random.Generator)
    assert isinstance(sm.parent_rng("order", "user_1"), np.random.Generator)
    assert isinstance(sm.row_rng("order", "user_1", 0), np.random.Generator)


def test_seed_manager_different_master_seeds():
    """Test that different master seeds produce different results."""
    sm1 = SeedManager(master_seed=42)
    sm2 = SeedManager(master_seed=43)

    seed1 = sm1.node_seed("user")
    seed2 = sm2.node_seed("user")

    assert seed1 != seed2

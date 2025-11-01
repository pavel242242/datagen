"""Primitive generators: sequence, choice, distribution, fanout."""

import numpy as np
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Sequence Generator
# ============================================================================

def generate_sequence(start: int, step: int, size: int) -> np.ndarray:
    """
    Generate sequential integers.

    Args:
        start: Starting value
        step: Step size
        size: Number of values to generate

    Returns:
        Array of sequential integers

    Examples:
        >>> generate_sequence(1, 1, 5)
        array([1, 2, 3, 4, 5])

        >>> generate_sequence(100, 10, 3)
        array([100, 110, 120])
    """
    return np.arange(start, start + step * size, step, dtype=int)


# ============================================================================
# Choice Generator
# ============================================================================

def normalize_weights(weights: list[float]) -> np.ndarray:
    """Normalize weights to sum to 1.0."""
    w = np.array(weights, dtype=float)
    total = w.sum()
    if total == 0:
        raise ValueError("Weights sum to zero")
    return w / total


def generate_zipf_weights(n: int, alpha: float = 1.5) -> np.ndarray:
    """
    Generate Zipf distribution weights.

    Args:
        n: Number of items
        alpha: Zipf exponent (higher = more skewed)

    Returns:
        Normalized weights following Zipf law
    """
    ranks = np.arange(1, n + 1)
    weights = 1.0 / (ranks ** alpha)
    return normalize_weights(weights.tolist())


def generate_head_tail_weights(
    n: int,
    head_share: float = 0.8,
    tail_alpha: float = 1.5
) -> np.ndarray:
    """
    Generate head-tail weights (popular items get head_share, rest follows Zipf).

    Args:
        n: Number of items
        head_share: Proportion of weight for head items (top 20%)
        tail_alpha: Zipf exponent for tail items

    Returns:
        Normalized weights
    """
    head_size = max(1, int(n * 0.2))  # Top 20% are "head"
    tail_size = n - head_size

    # Head items share head_share equally
    head_weight_each = head_share / head_size if head_size > 0 else 0

    # Tail items share (1 - head_share) via Zipf
    if tail_size > 0:
        tail_weights = generate_zipf_weights(tail_size, tail_alpha)
        tail_weights = tail_weights * (1.0 - head_share)
    else:
        tail_weights = np.array([])

    weights = np.concatenate([
        np.full(head_size, head_weight_each),
        tail_weights
    ])

    return normalize_weights(weights.tolist())


def generate_choice(
    choices: list[Any],
    size: int,
    rng: np.random.Generator,
    weights: Optional[list[float]] = None,
    weights_kind: Optional[str] = None
) -> np.ndarray:
    """
    Generate random choices from a list.

    Args:
        choices: List of values to choose from
        size: Number of values to generate
        rng: Random number generator
        weights: Optional explicit weights
        weights_kind: Optional weight distribution ("uniform", "zipf@alpha", "head_tail@params")

    Returns:
        Array of chosen values

    Examples:
        >>> rng = np.random.default_rng(42)
        >>> generate_choice(['a', 'b', 'c'], 5, rng)
        array(['a', 'c', 'b', 'a', 'c'], dtype='<U1')

        >>> generate_choice([1, 2, 3], 5, rng, weights=[0.5, 0.3, 0.2])
        array([1, 1, 2, 1, 3])
    """
    n = len(choices)
    if n == 0:
        raise ValueError("choices cannot be empty")

    # Determine weights
    if weights is not None:
        w = normalize_weights(weights)
    elif weights_kind == "uniform" or weights_kind is None:
        w = None  # numpy handles uniform by default
    elif weights_kind.startswith("zipf@"):
        alpha = float(weights_kind.split("@")[1])
        w = generate_zipf_weights(n, alpha)
    elif weights_kind.startswith("head_tail@"):
        # Parse head_tail@{head_share,tail_alpha}
        params = weights_kind.split("@")[1].strip("{}")
        parts = params.split(",")
        head_share = float(parts[0]) if len(parts) > 0 else 0.8
        tail_alpha = float(parts[1]) if len(parts) > 1 else 1.5
        w = generate_head_tail_weights(n, head_share, tail_alpha)
    else:
        logger.warning(f"Unknown weights_kind: {weights_kind}, using uniform")
        w = None

    # Sample
    indices = rng.choice(n, size=size, p=w)
    return np.array([choices[i] for i in indices])


# ============================================================================
# Distribution Generators
# ============================================================================

def clamp_values(values: np.ndarray, clamp: tuple[float, float]) -> np.ndarray:
    """Clamp values to [min, max] range."""
    return np.clip(values, clamp[0], clamp[1])


def generate_distribution(
    dist_type: str,
    params: dict,
    size: int,
    rng: np.random.Generator,
    clamp: tuple[float, float]
) -> np.ndarray:
    """
    Generate values from statistical distribution.

    Args:
        dist_type: "normal", "lognormal", "uniform", "poisson"
        params: Distribution parameters
        size: Number of values
        rng: Random number generator
        clamp: (min, max) bounds

    Returns:
        Array of values clamped to range

    Examples:
        >>> rng = np.random.default_rng(42)
        >>> vals = generate_distribution("normal", {"mean": 100, "std": 15}, 5, rng, (50, 150))
        >>> all(50 <= v <= 150 for v in vals)
        True
    """
    if dist_type == "normal":
        mean = params.get("mean", 0)
        std = params.get("std", 1)
        values = rng.normal(mean, std, size)

    elif dist_type == "lognormal":
        mean = params.get("mean", 0)
        sigma = params.get("sigma", 1)
        values = rng.lognormal(mean, sigma, size)

    elif dist_type == "uniform":
        low = params.get("low", 0)
        high = params.get("high", 1)
        values = rng.uniform(low, high, size)

    elif dist_type == "poisson":
        lam = params.get("lambda", 1.0)
        values = rng.poisson(lam, size).astype(float)

    else:
        raise ValueError(f"Unknown distribution type: {dist_type}")

    return clamp_values(values, clamp)


# ============================================================================
# Fanout Sampler
# ============================================================================

def sample_fanout(
    distribution: str,
    size: int,
    rng: np.random.Generator,
    lambda_: Optional[float] = None,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None
) -> np.ndarray:
    """
    Sample fanout counts for parent rows.

    Args:
        distribution: "poisson" or "uniform"
        size: Number of parent rows
        rng: Random number generator
        lambda_: Poisson lambda parameter
        min_val: Minimum fanout (inclusive)
        max_val: Maximum fanout (inclusive)

    Returns:
        Array of fanout counts (integers)

    Examples:
        >>> rng = np.random.default_rng(42)
        >>> counts = sample_fanout("poisson", 10, rng, lambda_=5, min_val=0, max_val=20)
        >>> all(0 <= c <= 20 for c in counts)
        True
    """
    if distribution == "poisson":
        if lambda_ is None:
            raise ValueError("Poisson fanout requires 'lambda' parameter")
        counts = rng.poisson(lambda_, size)

    elif distribution == "uniform":
        if min_val is None or max_val is None:
            raise ValueError("Uniform fanout requires 'min' and 'max' parameters")
        counts = rng.integers(min_val, max_val + 1, size)

    else:
        raise ValueError(f"Unknown fanout distribution: {distribution}")

    # Apply bounds
    if min_val is not None:
        counts = np.maximum(counts, min_val)
    if max_val is not None:
        counts = np.minimum(counts, max_val)

    return counts.astype(int)

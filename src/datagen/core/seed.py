"""Deterministic seed derivation for reproducibility."""

import hashlib
import numpy as np
from typing import Union


def derive_seed(*parts: Union[str, int, float]) -> int:
    """
    Derive a deterministic seed from input parts using SHA256.

    Args:
        *parts: Components to hash (master_seed, node_id, column_name, etc.)

    Returns:
        32-bit integer seed suitable for np.random.Generator

    Examples:
        >>> derive_seed(42, "user", "user_id")
        123456789  # deterministic based on inputs

        >>> derive_seed(42, "order", "customer_id", "parent_123")
        987654321
    """
    # Convert all parts to strings and concatenate
    combined = "|".join(str(p) for p in parts)

    # Hash using SHA256
    hash_bytes = hashlib.sha256(combined.encode("utf-8")).digest()

    # Take first 4 bytes and convert to int32
    seed = int.from_bytes(hash_bytes[:4], byteorder="big", signed=False)

    # Ensure it's within valid range for numpy (0 to 2^32-1)
    seed = seed % (2**32)

    return seed


def get_rng(*parts: Union[str, int, float]) -> np.random.Generator:
    """
    Get a numpy random generator with derived seed.

    Args:
        *parts: Components to derive seed from

    Returns:
        np.random.Generator instance

    Examples:
        >>> rng = get_rng(42, "user", "age")
        >>> values = rng.normal(30, 5, size=100)
    """
    seed = derive_seed(*parts)
    return np.random.default_rng(seed)


class SeedManager:
    """Manage seed derivation across scopes."""

    def __init__(self, master_seed: int = 42):
        self.master_seed = master_seed

    def node_seed(self, node_id: str) -> int:
        """Derive seed for a node."""
        return derive_seed(self.master_seed, node_id)

    def node_rng(self, node_id: str) -> np.random.Generator:
        """Get RNG for a node."""
        return get_rng(self.master_seed, node_id)

    def column_seed(self, node_id: str, column_name: str) -> int:
        """Derive seed for a specific column."""
        return derive_seed(self.master_seed, node_id, column_name)

    def column_rng(self, node_id: str, column_name: str) -> np.random.Generator:
        """Get RNG for a specific column."""
        return get_rng(self.master_seed, node_id, column_name)

    def parent_seed(self, node_id: str, parent_pk: Union[str, int]) -> int:
        """Derive seed for fanout from a specific parent."""
        return derive_seed(self.master_seed, node_id, "parent", parent_pk)

    def parent_rng(self, node_id: str, parent_pk: Union[str, int]) -> np.random.Generator:
        """Get RNG for fanout from a specific parent."""
        return get_rng(self.master_seed, node_id, "parent", parent_pk)

    def row_seed(self, node_id: str, parent_pk: Union[str, int], row_index: int) -> int:
        """Derive seed for a specific child row."""
        return derive_seed(self.master_seed, node_id, "parent", parent_pk, "row", row_index)

    def row_rng(
        self, node_id: str, parent_pk: Union[str, int], row_index: int
    ) -> np.random.Generator:
        """Get RNG for a specific child row."""
        return get_rng(self.master_seed, node_id, "parent", parent_pk, "row", row_index)

"""Generator registry and high-level dispatcher."""

import numpy as np
import pandas as pd
from typing import Any, Optional, Dict
import logging

from datagen.core.generators.primitives import (
    generate_sequence,
    generate_choice,
    generate_distribution,
    sample_fanout,
)
from datagen.core.generators.temporal import generate_datetime_series
from datagen.core.generators.semantic import generate_faker, resolve_locale

logger = logging.getLogger(__name__)


# ============================================================================
# Lookup Generator
# ============================================================================

class LookupResolver:
    """Resolves lookup references to other tables."""

    def __init__(self):
        self._data_cache: Dict[str, pd.DataFrame] = {}

    def register_table(self, table_id: str, df: pd.DataFrame):
        """Register a generated table for lookups."""
        self._data_cache[table_id] = df.copy()
        logger.debug(f"Registered table '{table_id}' with {len(df)} rows")

    def lookup(
        self,
        from_ref: str,
        size: int,
        rng: np.random.Generator,
        on: Optional[dict] = None,
        parent_data: Optional[pd.DataFrame] = None
    ) -> np.ndarray:
        """
        Lookup values from another table.

        Args:
            from_ref: Reference in format "table.column"
            size: Number of values to return
            rng: Random generator
            on: Optional join condition {"this_key": "other_key"}
            parent_data: Optional parent DataFrame for join-based lookups

        Returns:
            Array of looked-up values

        Examples:
            # Simple random lookup
            resolver.lookup("user.user_id", 100, rng)

            # Join-based lookup
            resolver.lookup(
                "product.name",
                100,
                rng,
                on={"product_id": "product_id"},
                parent_data=current_df
            )
        """
        # Parse reference
        if "." not in from_ref:
            raise ValueError(f"Invalid lookup reference: {from_ref}")

        table_id, column = from_ref.split(".", 1)

        if table_id not in self._data_cache:
            raise ValueError(f"Table '{table_id}' not found in cache. Available: {list(self._data_cache.keys())}")

        source_df = self._data_cache[table_id]

        if column not in source_df.columns:
            raise ValueError(f"Column '{column}' not found in table '{table_id}'")

        # If no join condition, randomly sample
        if on is None or parent_data is None:
            values = source_df[column].values
            indices = rng.choice(len(values), size=size, replace=True)
            return values[indices]

        # Join-based lookup
        # on format: {"this_key": "local_column_name"} or {"local_col": "source_col"}
        # The key is just a marker, the value is the actual column name
        local_col = list(on.values())[0]  # The column in parent_data
        source_col = list(on.values())[0]  # Same column name in source table (typically FK)

        # Actually, looking at the spec: {"this_key": "store_id"} means
        # join parent_data[store_id] with source_df[store_id]
        # So it's the same column name on both sides

        if local_col not in parent_data.columns:
            raise ValueError(f"Join key '{local_col}' not found in parent data. Available: {list(parent_data.columns)}")
        if source_col not in source_df.columns:
            # Try using the primary key of source table as fallback
            # For now, assume same column name
            raise ValueError(f"Join key '{source_col}' not found in source table '{table_id}'. Available: {list(source_df.columns)}")

        # Perform left join
        merged = parent_data[[local_col]].merge(
            source_df[[source_col, column]],
            left_on=local_col,
            right_on=source_col,
            how="left"
        )

        return merged[column].values


# ============================================================================
# Expression Generator
# ============================================================================

def generate_expression(code: str, context: pd.DataFrame) -> np.ndarray:
    """
    Evaluate simple arithmetic expression.

    Args:
        code: Expression code (e.g., "quantity * unit_price")
        context: DataFrame with column values

    Returns:
        Array of computed values

    Examples:
        >>> df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
        >>> generate_expression("a * b", df)
        array([10, 40, 90])

    Security:
        Only allows arithmetic operations on column names.
        No function calls, no imports, no attribute access.
    """
    # Simple whitelist-based evaluator
    # For MVP, use pandas eval which is safer than Python eval
    try:
        result = context.eval(code).values
        return result
    except Exception as e:
        raise ValueError(f"Expression evaluation failed: {code}. Error: {e}")


# ============================================================================
# Generator Registry
# ============================================================================

class GeneratorRegistry:
    """
    Central registry mapping generator specs to functions.

    This handles dispatching to the correct generator based on DSL spec.
    """

    def __init__(self, lookup_resolver: Optional[LookupResolver] = None):
        self.lookup_resolver = lookup_resolver or LookupResolver()

    def generate(
        self,
        spec: dict,
        size: int,
        rng: np.random.Generator,
        context: Optional[pd.DataFrame] = None,
        timeframe: Optional[dict] = None,
        extra_patterns: Optional[list] = None
    ) -> np.ndarray:
        """
        Generate values based on generator spec.

        Args:
            spec: Generator spec dict (exactly one key matching a generator type)
            size: Number of values to generate
            rng: Random generator
            context: Optional DataFrame context for expressions/locale_from
            timeframe: Optional timeframe dict for datetime_series
            extra_patterns: Optional list of additional patterns for datetime_series

        Returns:
            Array of generated values
        """
        # Determine generator type
        gen_type = self._get_generator_type(spec)

        if gen_type == "sequence":
            return self._gen_sequence(spec["sequence"], size)

        elif gen_type == "choice":
            return self._gen_choice(spec["choice"], size, rng)

        elif gen_type == "distribution":
            return self._gen_distribution(spec["distribution"], size, rng)

        elif gen_type == "datetime_series":
            return self._gen_datetime_series(spec["datetime_series"], size, rng, timeframe, extra_patterns)

        elif gen_type == "faker":
            return self._gen_faker(spec["faker"], size, rng, context)

        elif gen_type == "lookup":
            return self._gen_lookup(spec["lookup"], size, rng, context)

        elif gen_type == "expression":
            return self._gen_expression(spec["expression"], context)

        elif gen_type == "enum_list":
            # For vocab nodes, just return the values
            return np.array(spec["enum_list"]["values"])

        else:
            raise ValueError(f"Unknown generator type: {gen_type}")

    def _get_generator_type(self, spec: dict) -> str:
        """Extract generator type from spec."""
        valid_types = {
            "sequence", "choice", "distribution", "datetime_series",
            "faker", "lookup", "expression", "enum_list"
        }
        gen_types = set(spec.keys()) & valid_types
        if len(gen_types) != 1:
            raise ValueError(f"Spec must have exactly one generator type, found: {gen_types}")
        return list(gen_types)[0]

    def _gen_sequence(self, spec: dict, size: int) -> np.ndarray:
        start = spec.get("start", 1)
        step = spec.get("step", 1)
        return generate_sequence(start, step, size)

    def _gen_choice(self, spec: dict, size: int, rng: np.random.Generator) -> np.ndarray:
        choices = spec.get("choices")
        weights = spec.get("weights")
        weights_kind = spec.get("weights_kind")

        # Handle choices_ref (will be resolved by executor)
        if "choices_ref" in spec:
            raise ValueError("choices_ref must be resolved before generation")

        return generate_choice(choices, size, rng, weights, weights_kind)

    def _gen_distribution(self, spec: dict, size: int, rng: np.random.Generator) -> np.ndarray:
        dist_type = spec["type"]
        params = spec["params"]
        clamp = tuple(spec["clamp"])
        return generate_distribution(dist_type, params, size, rng, clamp)

    def _gen_datetime_series(
        self,
        spec: dict,
        size: int,
        rng: np.random.Generator,
        timeframe: Optional[dict],
        extra_patterns: Optional[list] = None
    ) -> pd.Series:
        within = spec["within"]

        if within == "timeframe":
            if timeframe is None:
                raise ValueError("datetime_series requires timeframe when within='timeframe'")
            start = timeframe["start"]
            end = timeframe["end"]
        elif isinstance(within, dict):
            start = within["start"]
            end = within["end"]
        else:
            raise ValueError(f"Invalid 'within' value: {within}")

        freq = spec["freq"]
        pattern = spec.get("pattern")

        # Combine pattern from spec with extra_patterns from modifiers
        all_patterns = []
        if pattern:
            all_patterns.append(pattern)
        if extra_patterns:
            all_patterns.extend(extra_patterns)

        if len(all_patterns) > 1:
            # Use composite patterns
            return generate_datetime_series(start, end, freq, size, rng, patterns=all_patterns)
        elif len(all_patterns) == 1:
            # Use single pattern
            return generate_datetime_series(start, end, freq, size, rng, pattern=all_patterns[0])
        else:
            # No patterns
            return generate_datetime_series(start, end, freq, size, rng)

    def _gen_faker(
        self,
        spec: dict,
        size: int,
        rng: np.random.Generator,
        context: Optional[pd.DataFrame]
    ) -> np.ndarray:
        method = spec["method"]
        locale_from = spec.get("locale_from")

        if locale_from and context is not None:
            # Resolve locale from context column
            if locale_from not in context.columns:
                raise ValueError(f"locale_from column '{locale_from}' not found in context")

            locale_values = context[locale_from].values
            return generate_faker(method, size, rng, locale_from_values=locale_values)
        else:
            return generate_faker(method, size, rng)

    def _gen_lookup(
        self,
        spec: dict,
        size: int,
        rng: np.random.Generator,
        context: Optional[pd.DataFrame]
    ) -> np.ndarray:
        from_ref = spec["from"]
        on = spec.get("on")

        return self.lookup_resolver.lookup(from_ref, size, rng, on, context)

    def _gen_expression(self, spec: dict, context: Optional[pd.DataFrame]) -> np.ndarray:
        if context is None:
            raise ValueError("Expression generator requires context DataFrame")

        code = spec["code"]
        return generate_expression(code, context)


# ============================================================================
# Global registry instance
# ============================================================================

_global_registry = GeneratorRegistry()


def get_registry() -> GeneratorRegistry:
    """Get the global generator registry."""
    return _global_registry

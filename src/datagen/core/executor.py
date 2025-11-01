"""Main execution engine for dataset generation."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import logging

from datagen.core.schema import Dataset, Node
from datagen.core.dag import build_dag
from datagen.core.seed import SeedManager
from datagen.core.generators.registry import GeneratorRegistry
from datagen.core.generators.primitives import sample_fanout
from datagen.core.modifiers import apply_modifiers

logger = logging.getLogger(__name__)


class DatasetExecutor:
    """Execute dataset generation according to DSL."""

    def __init__(self, dataset: Dataset, master_seed: int = 42):
        self.dataset = dataset
        self.seed_manager = SeedManager(master_seed)
        self.registry = GeneratorRegistry()

        # Build DAG
        self.dag = build_dag(dataset)
        self.nodes_by_id = {n.id: n for n in dataset.nodes}

        # Storage for generated data
        self.generated_data = {}

    def execute(self, output_dir: Optional[Path] = None) -> dict[str, pd.DataFrame]:
        """
        Execute full dataset generation.

        Args:
            output_dir: Optional directory to write Parquet files

        Returns:
            Dictionary of {table_id: DataFrame}
        """
        logger.info(f"Starting dataset generation: {self.dataset.metadata.name}")
        logger.info(f"DAG has {len(self.dag)} levels")

        # Generate each level in order
        for level_idx, level in enumerate(self.dag):
            logger.info(f"Generating level {level_idx}: {level}")

            for node_id in level:
                node = self.nodes_by_id[node_id]
                df = self.generate_node(node)

                # Register with lookup resolver
                self.registry.lookup_resolver.register_table(node_id, df)

                # Store
                self.generated_data[node_id] = df

                logger.info(f"  {node_id}: {len(df)} rows, {len(df.columns)} columns")

        logger.info("Dataset generation complete")

        # Write to disk if requested
        if output_dir:
            self.write_output(output_dir)

        return self.generated_data

    def generate_node(self, node: Node) -> pd.DataFrame:
        """Generate data for a single node (entity, fact, or vocab)."""
        if node.kind == "entity":
            return self.generate_entity(node)
        elif node.kind == "vocab":
            return self.generate_vocab(node)
        else:
            return self.generate_fact(node)

    def generate_entity(self, node: Node) -> pd.DataFrame:
        """
        Generate entity table (no parents).
        """
        # Use configured row count or default to 1000
        n_rows = node.rows if node.rows is not None else 1000

        logger.debug(f"Generating entity '{node.id}' with {n_rows} rows")

        data = {}
        rng = self.seed_manager.node_rng(node.id)

        # First pass: identify self-referential lookup columns
        lookup_columns = []
        for col in node.columns:
            # Check if this is a self-referential lookup
            is_self_lookup = False
            if col.generator and isinstance(col.generator, dict) and "lookup" in col.generator:
                lookup_ref = col.generator["lookup"].get("from")
                if lookup_ref and "." in lookup_ref:
                    ref_table = lookup_ref.split(".")[0]
                    if ref_table == node.id:
                        is_self_lookup = True
                        lookup_columns.append(col)

            if not is_self_lookup:
                col_rng = self.seed_manager.column_rng(node.id, col.name)

                # Generate base values
                values = self._generate_column(col, n_rows, col_rng, context=None)

                # Apply modifiers if present
                if col.modifiers:
                    # For entities, context is just the current data so far
                    context_df = self._build_context_with_effects(data, col.modifiers)
                    values = apply_modifiers(values, col.modifiers, col_rng, context_df)

                # Cast to target dtype
                values = self._cast_to_dtype(values, col.type, col.nullable)

                data[col.name] = values

        # Add partial table to cache for self-references
        if lookup_columns:
            partial_df = pd.DataFrame(data)
            self.generated_data[node.id] = partial_df
            # Also register with lookup resolver so self-references can work
            self.registry.lookup_resolver.register_table(node.id, partial_df)

        # Second pass: generate self-referential lookup columns
        for col in lookup_columns:
            col_rng = self.seed_manager.column_rng(node.id, col.name)

            # Generate base values (now the table is in cache)
            values = self._generate_column(col, n_rows, col_rng, context=None)

            # Apply modifiers if present
            if col.modifiers:
                context_df = self._build_context_with_effects(data, col.modifiers)
                values = apply_modifiers(values, col.modifiers, col_rng, context_df)

            # Cast to target dtype
            values = self._cast_to_dtype(values, col.type, col.nullable)

            data[col.name] = values

        df = pd.DataFrame(data)
        return df

    def generate_vocab(self, node: Node) -> pd.DataFrame:
        """
        Generate vocabulary/taxonomy table using enum_list generator.
        Vocab tables have a fixed set of values defined in the schema.
        """
        logger.debug(f"Generating vocab '{node.id}'")

        data = {}
        rng = self.seed_manager.node_rng(node.id)

        # Find the column with enum_list generator (typically the PK)
        enum_column = None
        for col in node.columns:
            if "enum_list" in col.generator:
                enum_column = col
                break

        if not enum_column:
            raise ValueError(f"Vocab node '{node.id}' must have an enum_list generator")

        # Get enum values to determine row count
        enum_values = enum_column.generator["enum_list"]["values"]
        n_rows = len(enum_values)

        # Generate all columns
        for col in node.columns:
            col_rng = self.seed_manager.column_rng(node.id, col.name)

            # Generate values
            values = self._generate_column(col, n_rows, col_rng, context=None)

            # Apply modifiers if present
            if col.modifiers:
                context_df = self._build_context_with_effects(data, col.modifiers)
                values = apply_modifiers(values, col.modifiers, col_rng, context_df)

            # Cast to target dtype
            values = self._cast_to_dtype(values, col.type, col.nullable)

            data[col.name] = values

        df = pd.DataFrame(data)
        return df

    def generate_fact(self, node: Node) -> pd.DataFrame:
        """
        Generate fact table with parent fanout.

        For MVP, we support one primary parent.
        """
        if not node.parents:
            # Fact with no parents - treat like entity but with timeframe
            return self.generate_entity(node)

        # Get primary parent (first in list)
        primary_parent_id = node.parents[0]

        if primary_parent_id not in self.generated_data:
            raise ValueError(
                f"Parent '{primary_parent_id}' not generated yet for fact '{node.id}'"
            )

        parent_df = self.generated_data[primary_parent_id]
        parent_node = self.nodes_by_id[primary_parent_id]

        logger.debug(
            f"Generating fact '{node.id}' from parent '{primary_parent_id}' "
            f"({len(parent_df)} parent rows)"
        )

        # Sample fanout for each parent row
        if node.fanout:
            fanout_counts = self._sample_fanout(node, len(parent_df))
        else:
            # Default: 1 child per parent
            fanout_counts = np.ones(len(parent_df), dtype=int)

        # Apply table-level effect modifiers to scale fanout
        if node.modifiers:
            # Collect all parent data for join key lookups
            all_parents_df = parent_df.copy()
            # Add other parents if multiple parents exist
            if node.parents and len(node.parents) > 1:
                for parent_id in node.parents[1:]:
                    if parent_id in self.generated_data:
                        other_parent = self.generated_data[parent_id]
                        # For MVP, just add columns not already present
                        for col in other_parent.columns:
                            if col not in all_parents_df.columns:
                                # Assume first row for now (simplified)
                                all_parents_df[col] = other_parent[col].iloc[0]

            fanout_counts = self._apply_table_effects_to_fanout(
                node, fanout_counts, all_parents_df
            )

        total_rows = fanout_counts.sum()
        logger.debug(f"  Total fanout: {total_rows} child rows (mean={fanout_counts.mean():.2f})")

        # Build child row mapping
        parent_indices = np.repeat(np.arange(len(parent_df)), fanout_counts)

        # Generate columns
        data = {}
        rng = self.seed_manager.node_rng(node.id)

        for col in node.columns:
            col_rng = self.seed_manager.column_rng(node.id, col.name)

            # Check if this is a lookup from parent
            if "lookup" in col.generator:
                from_ref = col.generator["lookup"]["from"]
                table_id = from_ref.split(".")[0]

                if table_id == primary_parent_id:
                    # Direct parent lookup - just repeat parent values
                    column_name = from_ref.split(".")[1]
                    parent_values = parent_df[column_name].values
                    values = parent_values[parent_indices]
                else:
                    # Lookup from other table
                    context_df = pd.DataFrame(data) if data else None
                    values = self._generate_column(col, total_rows, col_rng, context_df)
            else:
                # Regular generation
                context_df = pd.DataFrame(data) if data else None
                values = self._generate_column(col, total_rows, col_rng, context_df)

            # Apply modifiers
            if col.modifiers:
                # Special handling: for datetime columns, extract seasonality modifiers
                # and apply them during generation instead of as modifiers
                if col.type in ["datetime", "date"]:
                    # Filter out seasonality and outliers - these should affect occurrence, not values
                    remaining_modifiers = [
                        m for m in col.modifiers
                        if not (hasattr(m, 'transform') and m.transform in ['seasonality', 'outliers'])
                        and not (isinstance(m, dict) and m.get('transform') in ['seasonality', 'outliers'])
                    ]
                    if remaining_modifiers:
                        context_df = self._build_context_with_effects(data, col.modifiers)
                        values = apply_modifiers(values, remaining_modifiers, col_rng, context_df)
                else:
                    context_df = self._build_context_with_effects(data, col.modifiers)
                    values = apply_modifiers(values, col.modifiers, col_rng, context_df)

            # Cast
            values = self._cast_to_dtype(values, col.type, col.nullable)

            data[col.name] = values

        df = pd.DataFrame(data)
        return df

    def _generate_column(
        self,
        col,
        size: int,
        rng: np.random.Generator,
        context: Optional[pd.DataFrame]
    ) -> np.ndarray:
        """Generate values for a column."""
        timeframe = {
            "start": self.dataset.timeframe.start,
            "end": self.dataset.timeframe.end,
        }

        # For datetime columns, extract seasonality modifiers and pass as patterns
        extra_patterns = None
        if col.type in ["datetime", "date"] and col.modifiers:
            patterns = []
            for modifier in col.modifiers:
                if hasattr(modifier, 'transform'):
                    transform = modifier.transform
                    args = modifier.args
                else:
                    transform = modifier.get('transform')
                    args = modifier.get('args', {})

                if transform == 'seasonality':
                    patterns.append({
                        "dimension": args["dimension"],
                        "weights": args["weights"]
                    })

            if patterns:
                extra_patterns = patterns

        result = self.registry.generate(
            col.generator,
            size,
            rng,
            context=context,
            timeframe=timeframe,
            extra_patterns=extra_patterns
        )

        # Convert pandas Series to numpy array if needed
        if isinstance(result, pd.Series):
            return result.values

        return result

    def _sample_fanout(self, node: Node, n_parents: int) -> np.ndarray:
        """Sample fanout counts for parents."""
        fanout_spec = node.fanout
        rng = self.seed_manager.node_rng(node.id)

        return sample_fanout(
            fanout_spec.distribution,
            n_parents,
            rng,
            lambda_=fanout_spec.lambda_,
            min_val=fanout_spec.min,
            max_val=fanout_spec.max
        )

    def _apply_table_effects_to_fanout(
        self,
        node: Node,
        fanout_counts: np.ndarray,
        parent_df: pd.DataFrame
    ) -> np.ndarray:
        """
        Apply table-level effect modifiers to scale fanout counts.

        For each parent row, finds matching effects and multiplies fanout.
        """
        result_counts = fanout_counts.copy().astype(float)

        for modifier in node.modifiers:
            if hasattr(modifier, 'transform'):
                transform = modifier.transform
                args = modifier.args
            else:
                transform = modifier.get('transform')
                args = modifier.get('args', {})

            if transform != 'effect':
                continue

            effect_table_name = args.get('effect_table')
            if not effect_table_name or effect_table_name not in self.generated_data:
                logger.warning(f"Effect table {effect_table_name} not found, skipping table-level effect")
                continue

            effect_df = self.generated_data[effect_table_name]
            on = args.get('on', {})
            window = args.get('window', {})
            map_spec = args.get('map', {})

            start_col = window.get('start_col')
            end_col = window.get('end_col')
            field = map_spec.get('field')
            op = map_spec.get('op', 'mul')
            default = map_spec.get('default', 1.0)

            # Find timestamp column in parent for window matching
            timestamp_col = None
            for col in parent_df.columns:
                if pd.api.types.is_datetime64_any_dtype(parent_df[col]):
                    timestamp_col = col
                    break

            if timestamp_col:
                parent_timestamps = pd.to_datetime(parent_df[timestamp_col])
            else:
                # Use timeframe midpoint as default if no timestamp in parent
                timeframe_start = pd.to_datetime(self.dataset.timeframe.start)
                timeframe_end = pd.to_datetime(self.dataset.timeframe.end)
                default_timestamp = timeframe_start + (timeframe_end - timeframe_start) / 2
                parent_timestamps = pd.Series([default_timestamp] * len(parent_df))

            # For each parent row, find matching effect and apply multiplier
            for idx in range(len(parent_df)):
                parent_timestamp = parent_timestamps.iloc[idx]

                # Filter effects by join keys
                matching_effects = effect_df.copy()

                if on:  # If there are join keys
                    for local_key, effect_key in on.items():
                        if local_key not in parent_df.columns:
                            continue
                        local_value = parent_df[local_key].iloc[idx]
                        matching_effects = matching_effects[matching_effects[effect_key] == local_value]

                # Filter by time window
                if start_col and end_col and start_col in effect_df.columns and end_col in effect_df.columns:
                    effect_start = pd.to_datetime(matching_effects[start_col]).dt.tz_localize(None)
                    effect_end = pd.to_datetime(matching_effects[end_col]).dt.tz_localize(None)
                    parent_ts_normalized = pd.to_datetime(parent_timestamp).tz_localize(None) if hasattr(parent_timestamp, 'tz_localize') else parent_timestamp

                    matching_effects = matching_effects[
                        (effect_start <= parent_ts_normalized) &
                        (effect_end >= parent_ts_normalized)
                    ]

                # Apply effect multiplier to fanout
                if len(matching_effects) > 0:
                    if field in matching_effects.columns:
                        effect_value = float(matching_effects[field].iloc[0])
                    else:
                        # Field doesn't exist but effect matches - use 1.0 (active) instead of default
                        effect_value = 1.0
                else:
                    effect_value = default

                if op == 'mul':
                    result_counts[idx] *= effect_value
                elif op == 'add':
                    result_counts[idx] += effect_value

        # Round and convert back to int, ensuring non-negative
        return np.maximum(0, np.round(result_counts)).astype(int)

    def _build_context_with_effects(self, data: dict, modifiers: list) -> pd.DataFrame:
        """
        Build context DataFrame with effect tables embedded.

        Scans modifiers for effect transforms and adds referenced effect tables
        as special columns prefixed with _effect_.
        """
        context_df = pd.DataFrame(data) if data else pd.DataFrame()

        # Find effect tables referenced in modifiers
        for modifier in modifiers:
            if hasattr(modifier, 'transform'):
                transform = modifier.transform
                args = modifier.args
            else:
                transform = modifier.get('transform')
                args = modifier.get('args', {})

            if transform == 'effect':
                effect_table_name = args.get('effect_table')
                if effect_table_name and effect_table_name in self.generated_data:
                    # Add effect table as a column (each row gets the full table)
                    effect_df = self.generated_data[effect_table_name]
                    context_df[f"_effect_{effect_table_name}"] = [effect_df] * len(context_df) if len(context_df) > 0 else []

        return context_df

    def _cast_to_dtype(self, values: np.ndarray, dtype_str: str, nullable: bool) -> np.ndarray:
        """Cast values to target dtype."""
        if dtype_str == "int":
            return values.astype(int)
        elif dtype_str == "float":
            return values.astype(float)
        elif dtype_str == "string":
            return values.astype(str)
        elif dtype_str == "bool":
            return values.astype(bool)
        elif dtype_str in ["datetime", "date"]:
            return pd.to_datetime(values)
        else:
            logger.warning(f"Unknown dtype: {dtype_str}, returning as-is")
            return values

    def write_output(self, output_dir: Path):
        """Write generated data to Parquet files."""
        from datagen.core.output import write_parquet, write_metadata

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Writing {len(self.generated_data)} tables to {output_dir}")

        for table_id, df in self.generated_data.items():
            parquet_path = output_dir / f"{table_id}.parquet"
            write_parquet(df, parquet_path)
            logger.info(f"  Wrote {table_id}.parquet ({len(df)} rows)")

        # Write metadata
        metadata = {
            "dataset_name": self.dataset.metadata.name,
            "version": self.dataset.version,
            "master_seed": self.seed_manager.master_seed,
            "tables": {
                table_id: {"rows": len(df), "columns": len(df.columns)}
                for table_id, df in self.generated_data.items()
            }
        }

        write_metadata(metadata, output_dir / ".metadata.json")
        logger.info("  Wrote .metadata.json")


def generate_dataset(
    dataset: Dataset,
    master_seed: int = 42,
    output_dir: Optional[Path] = None
) -> dict[str, pd.DataFrame]:
    """
    Main entry point for dataset generation.

    Args:
        dataset: Validated dataset schema
        master_seed: Seed for reproducibility
        output_dir: Optional output directory for Parquet files

    Returns:
        Dictionary of generated DataFrames
    """
    executor = DatasetExecutor(dataset, master_seed)
    return executor.execute(output_dir)

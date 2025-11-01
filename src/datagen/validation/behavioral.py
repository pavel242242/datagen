"""
Behavioral validators for generated datasets.

Validates:
- Weekend share targets
- Mean in range targets
- Composite effect targets (basic)
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path

from ..core.schema import Dataset
from .structural import ValidationResult


class BehavioralValidator:
    """Validates behavioral properties of generated data."""

    def __init__(self, dataset: Dataset, data_dir: Path):
        self.dataset = dataset
        self.data_dir = data_dir
        self.tables: Dict[str, pd.DataFrame] = {}

    def load_tables(self) -> None:
        """Load all generated Parquet files."""
        for node in self.dataset.nodes:
            parquet_path = self.data_dir / f"{node.id}.parquet"
            if parquet_path.exists():
                self.tables[node.id] = pd.read_parquet(parquet_path)

    def validate_all(self) -> List[ValidationResult]:
        """Run all behavioral validations."""
        results = []

        # Load all tables first
        self.load_tables()

        # Validate targets if defined
        if not self.dataset.targets:
            return results

        # Weekend share target
        if self.dataset.targets.weekend_share:
            result = self._validate_weekend_share(self.dataset.targets.weekend_share)
            if result:
                results.append(result)

        # Mean in range target
        if self.dataset.targets.mean_in_range:
            result = self._validate_mean_in_range(self.dataset.targets.mean_in_range)
            if result:
                results.append(result)

        # Composite effect target
        if self.dataset.targets.composite_effect:
            result = self._validate_composite_effect(self.dataset.targets.composite_effect)
            if result:
                results.append(result)

        return results

    def _validate_weekend_share(self, target) -> Optional[ValidationResult]:
        """Validate weekend share target."""
        table = target.table
        timestamp = target.timestamp
        min_share = target.min
        max_share = target.max

        if table not in self.tables:
            return ValidationResult(
                name=f"{table}.weekend_share",
                passed=False,
                message=f"Table {table} not found",
                details={"table": table}
            )

        df = self.tables[table]

        if timestamp not in df.columns:
            return ValidationResult(
                name=f"{table}.weekend_share",
                passed=False,
                message=f"Timestamp column {timestamp} not found",
                details={"table": table, "timestamp": timestamp}
            )

        # Parse timestamp and compute weekend share
        dt_col = pd.to_datetime(df[timestamp])
        is_weekend = dt_col.dt.dayofweek >= 5  # Saturday=5, Sunday=6
        weekend_count = is_weekend.sum()
        total_count = len(df)
        actual_share = weekend_count / total_count if total_count > 0 else 0

        passed = min_share <= actual_share <= max_share

        return ValidationResult(
            name=f"{table}.weekend_share",
            passed=passed,
            message=f"Weekend share {actual_share:.3f} (target: [{min_share:.3f}, {max_share:.3f}])",
            details={
                "table": table,
                "timestamp_column": timestamp,
                "actual_share": float(actual_share),
                "min_share": min_share,
                "max_share": max_share,
                "weekend_count": int(weekend_count),
                "total_count": int(total_count)
            }
        )

    def _validate_mean_in_range(self, target) -> Optional[ValidationResult]:
        """Validate mean in range target."""
        table = target.table
        column = target.column
        min_mean = target.min
        max_mean = target.max

        if table not in self.tables:
            return ValidationResult(
                name=f"{table}.{column}.mean_in_range",
                passed=False,
                message=f"Table {table} not found",
                details={"table": table}
            )

        df = self.tables[table]

        if column not in df.columns:
            return ValidationResult(
                name=f"{table}.{column}.mean_in_range",
                passed=False,
                message=f"Column {column} not found",
                details={"table": table, "column": column}
            )

        col_data = df[column].dropna()
        if len(col_data) == 0:
            return ValidationResult(
                name=f"{table}.{column}.mean_in_range",
                passed=False,
                message=f"No data in column {column}",
                details={"table": table, "column": column}
            )

        actual_mean = float(col_data.mean())
        passed = min_mean <= actual_mean <= max_mean

        return ValidationResult(
            name=f"{table}.{column}.mean_in_range",
            passed=passed,
            message=f"Mean {actual_mean:.2f} (target: [{min_mean:.2f}, {max_mean:.2f}])",
            details={
                "table": table,
                "column": column,
                "actual_mean": actual_mean,
                "min_mean": min_mean,
                "max_mean": max_mean,
                "sample_size": int(len(col_data))
            }
        )

    def _validate_composite_effect(self, target) -> Optional[ValidationResult]:
        """
        Validate composite effect on metric distribution.

        Validates that the actual distribution of records matches the expected
        distribution from composite influences (seasonality, effects, outliers).
        """
        table = target.table
        metric = target.metric
        influences = target.influences
        tolerance = target.tolerance

        if table not in self.tables:
            return ValidationResult(
                name=f"{table}.composite_effect",
                passed=False,
                message=f"Table {table} not found",
                details={"table": table}
            )

        df = self.tables[table]

        # For occurrence_rate metric, we need to find the timestamp column
        # Look for datetime columns in the table
        timestamp_col = None
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                timestamp_col = col
                break

        if timestamp_col is None:
            return ValidationResult(
                name=f"{table}.composite_effect",
                passed=False,
                message=f"No datetime column found in table {table}",
                details={"table": table, "metric": metric}
            )

        # Extract timestamps and convert to datetime
        dt_col = pd.to_datetime(df[timestamp_col])

        # Calculate expected distribution from influences
        expected_weights = {}
        outlier_drop_rate = 0.0

        for influence in influences:
            if influence.kind == "seasonality":
                dim = influence.dimension
                weights = influence.weights

                if dim == "dow":
                    # Day of week: 0=Monday, 6=Sunday
                    expected_weights['dow'] = weights
                elif dim == "hour":
                    # Hour of day: 0-23
                    expected_weights['hour'] = weights
                elif dim == "month":
                    # Month: 1-12 (need to adjust index)
                    expected_weights['month'] = weights

            elif influence.kind == "outliers":
                # Outliers reduce overall count
                if influence.mode == "drop":
                    outlier_drop_rate = influence.rate

        # Calculate actual distribution
        actual_dist = {}

        # Build multidimensional distribution
        if 'dow' in expected_weights and 'hour' in expected_weights:
            # 2D distribution: dow × hour
            dow_weights = np.array(expected_weights['dow'])
            hour_weights = np.array(expected_weights['hour'])

            # Create expected distribution (7 days × 24 hours)
            expected_2d = np.outer(dow_weights, hour_weights)

            # Normalize to sum to 1
            expected_2d = expected_2d / expected_2d.sum()

            # Note: outlier drop rate in the validation target is aspirational -
            # it's only applied if the column actually has an outliers modifier
            # So we don't apply it to the expected distribution here

            # Calculate actual distribution
            dow_actual = dt_col.dt.dayofweek.values  # 0=Monday, 6=Sunday
            hour_actual = dt_col.dt.hour.values

            # Build 2D histogram
            actual_2d = np.zeros((7, 24))
            for d, h in zip(dow_actual, hour_actual):
                actual_2d[d, h] += 1

            # Normalize
            if actual_2d.sum() > 0:
                actual_2d = actual_2d / actual_2d.sum()

            # Calculate MAE and MAPE
            mae = np.mean(np.abs(actual_2d - expected_2d))

            # MAPE: avoid division by zero and very small denominators
            # Only consider cells with expected probability >= 0.3% to avoid extreme MAPE values
            # from low-probability time periods (e.g., weekend hours, early morning hours)
            mask = expected_2d >= 0.003
            if mask.sum() > 0:
                mape = np.mean(np.abs((actual_2d[mask] - expected_2d[mask]) / expected_2d[mask])) * 100
            else:
                mape = 0.0

            # Check tolerance
            mae_threshold = tolerance.get('mae', 0.05)
            mape_threshold = tolerance.get('mape', 10.0)

            mae_passed = mae <= mae_threshold
            mape_passed = mape <= mape_threshold
            passed = mae_passed and mape_passed

            return ValidationResult(
                name=f"{table}.composite_effect",
                passed=passed,
                message=f"MAE={mae:.4f} (≤{mae_threshold:.4f}), MAPE={mape:.1f}% (≤{mape_threshold:.1f}%)",
                details={
                    "table": table,
                    "metric": metric,
                    "timestamp_column": timestamp_col,
                    "mae": float(mae),
                    "mae_threshold": mae_threshold,
                    "mae_passed": mae_passed,
                    "mape": float(mape),
                    "mape_threshold": mape_threshold,
                    "mape_passed": mape_passed,
                    "sample_size": len(df),
                    "dimensions": ["dow", "hour"],
                    "outlier_drop_rate": outlier_drop_rate
                }
            )

        elif 'dow' in expected_weights:
            # 1D distribution: dow only
            dow_weights = np.array(expected_weights['dow'])
            expected_1d = dow_weights / dow_weights.sum()
            # Note: not applying outlier drop - see comment above

            dow_actual = dt_col.dt.dayofweek.values
            actual_1d = np.zeros(7)
            for d in dow_actual:
                actual_1d[d] += 1

            if actual_1d.sum() > 0:
                actual_1d = actual_1d / actual_1d.sum()

            mae = np.mean(np.abs(actual_1d - expected_1d))
            # Only consider values with expected probability >= 0.3%
            mask = expected_1d >= 0.003
            if mask.sum() > 0:
                mape = np.mean(np.abs((actual_1d[mask] - expected_1d[mask]) / expected_1d[mask])) * 100
            else:
                mape = 0.0

            mae_threshold = tolerance.get('mae', 0.05)
            mape_threshold = tolerance.get('mape', 10.0)
            mae_passed = mae <= mae_threshold
            mape_passed = mape <= mape_threshold
            passed = mae_passed and mape_passed

            return ValidationResult(
                name=f"{table}.composite_effect",
                passed=passed,
                message=f"MAE={mae:.4f} (≤{mae_threshold:.4f}), MAPE={mape:.1f}% (≤{mape_threshold:.1f}%)",
                details={
                    "table": table,
                    "metric": metric,
                    "timestamp_column": timestamp_col,
                    "mae": float(mae),
                    "mae_threshold": mae_threshold,
                    "mae_passed": mae_passed,
                    "mape": float(mape),
                    "mape_threshold": mape_threshold,
                    "mape_passed": mape_passed,
                    "sample_size": len(df),
                    "dimensions": ["dow"],
                    "outlier_drop_rate": outlier_drop_rate
                }
            )

        else:
            # No recognized seasonality dimensions
            return ValidationResult(
                name=f"{table}.composite_effect",
                passed=False,
                message=f"No recognized seasonality dimensions in influences",
                details={"table": table, "metric": metric, "influences": [i.kind for i in influences]}
            )

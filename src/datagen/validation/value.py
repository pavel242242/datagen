"""
Value validators for generated datasets.

Validates:
- Range constraints (min/max)
- Inequality constraints (column comparisons)
- Pattern constraints (regex)
- Enum constraints (allowed values)
"""

from typing import Dict, List
import pandas as pd
import numpy as np
from pathlib import Path
import re

from ..core.schema import Dataset
from .structural import ValidationResult


class ValueValidator:
    """Validates value constraints on generated data."""

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
        """Run all value validations."""
        results = []

        # Load all tables first
        self.load_tables()

        # Validate constraints from dataset.constraints
        if self.dataset.constraints.ranges:
            for constraint in self.dataset.constraints.ranges:
                result = self._validate_range(constraint)
                if result:
                    results.append(result)

        if self.dataset.constraints.inequalities:
            for constraint in self.dataset.constraints.inequalities:
                result = self._validate_inequality(constraint)
                if result:
                    results.append(result)

        if self.dataset.constraints.pattern:
            for constraint in self.dataset.constraints.pattern:
                result = self._validate_pattern(constraint)
                if result:
                    results.append(result)

        if self.dataset.constraints.enum:
            for constraint in self.dataset.constraints.enum:
                result = self._validate_enum(constraint)
                if result:
                    results.append(result)

        return results

    def _parse_attr(self, attr: str) -> tuple[str, str]:
        """Parse table.column format."""
        parts = attr.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid attr format: {attr}")
        return parts[0], parts[1]

    def _validate_range(self, constraint) -> ValidationResult:
        """Validate range constraint: min <= column <= max."""
        table, column = self._parse_attr(constraint.attr)
        min_val = constraint.min
        max_val = constraint.max

        if table not in self.tables:
            return ValidationResult(
                name=f"{table}.{column}.range",
                passed=False,
                message=f"Table {table} not found",
                details={"table": table, "column": column}
            )

        df = self.tables[table]

        if column not in df.columns:
            return ValidationResult(
                name=f"{table}.{column}.range",
                passed=False,
                message=f"Column {column} not found for range validation",
                details={"table": table, "column": column}
            )

        col_data = df[column].dropna()
        total = len(col_data)

        violations = 0
        if min_val is not None:
            violations += (col_data < min_val).sum()
        if max_val is not None:
            violations += (col_data > max_val).sum()

        passed = violations == 0
        valid_count = total - violations

        range_str = f"[{min_val if min_val is not None else '-∞'}, {max_val if max_val is not None else '∞'}]"

        return ValidationResult(
            name=f"{table}.{column}.range",
            passed=passed,
            message=f"Range {range_str}: {valid_count}/{total} values in range",
            details={
                "table": table,
                "column": column,
                "min": min_val,
                "max": max_val,
                "total_values": int(total),
                "valid_values": int(valid_count),
                "violations": int(violations),
                "actual_min": float(col_data.min()),
                "actual_max": float(col_data.max())
            }
        )

    def _validate_inequality(self, constraint) -> ValidationResult:
        """Validate inequality constraint: left_col op right_col."""
        # Parse left and right (can be table.column format or just column)
        left_parts = constraint.left.split(".")
        right_parts = constraint.right.split(".")

        # Both must be from same table
        if len(left_parts) == 2 and len(right_parts) == 2:
            left_table, left_col = left_parts
            right_table, right_col = right_parts
            if left_table != right_table:
                return ValidationResult(
                    name=f"inequality.{constraint.left}_{constraint.op}_{constraint.right}",
                    passed=False,
                    message=f"Cross-table inequality not supported",
                    details={"left": constraint.left, "right": constraint.right}
                )
            table = left_table
        elif len(left_parts) == 2:
            table, left_col = left_parts
            right_col = constraint.right
        elif len(right_parts) == 2:
            table, right_col = right_parts
            left_col = constraint.left
        else:
            return ValidationResult(
                name=f"inequality.{constraint.left}_{constraint.op}_{constraint.right}",
                passed=False,
                message=f"Cannot determine table for inequality",
                details={"left": constraint.left, "right": constraint.right}
            )

        if table not in self.tables:
            return ValidationResult(
                name=f"{table}.inequality.{left_col}_{constraint.op}_{right_col}",
                passed=False,
                message=f"Table {table} not found",
                details={"table": table}
            )

        df = self.tables[table]

        if left_col not in df.columns:
            return ValidationResult(
                name=f"{table}.inequality.{left_col}_{constraint.op}_{right_col}",
                passed=False,
                message=f"Left column {left_col} not found",
                details={"table": table, "left_column": left_col}
            )

        if right_col not in df.columns:
            return ValidationResult(
                name=f"{table}.inequality.{left_col}_{constraint.op}_{right_col}",
                passed=False,
                message=f"Right column {right_col} not found",
                details={"table": table, "right_column": right_col}
            )

        left_data = df[left_col].dropna()
        right_data = df[right_col].dropna()

        # Align indices
        valid_idx = left_data.index.intersection(right_data.index)
        left_data = left_data.loc[valid_idx]
        right_data = right_data.loc[valid_idx]

        total = len(valid_idx)

        operator = constraint.op
        if operator == "<":
            satisfied = (left_data < right_data).sum()
        elif operator == "<=":
            satisfied = (left_data <= right_data).sum()
        elif operator == ">":
            satisfied = (left_data > right_data).sum()
        elif operator == ">=":
            satisfied = (left_data >= right_data).sum()
        elif operator == "==":
            satisfied = (left_data == right_data).sum()
        else:
            return ValidationResult(
                name=f"{table}.inequality.{left_col}_{operator}_{right_col}",
                passed=False,
                message=f"Unknown operator: {operator}",
                details={"operator": operator}
            )

        violations = total - satisfied
        passed = violations == 0

        return ValidationResult(
            name=f"{table}.inequality.{left_col}_{operator}_{right_col}",
            passed=passed,
            message=f"Inequality {left_col} {operator} {right_col}: {satisfied}/{total} satisfied",
            details={
                "table": table,
                "left_column": left_col,
                "right_column": right_col,
                "operator": operator,
                "total_comparisons": int(total),
                "satisfied": int(satisfied),
                "violations": int(violations)
            }
        )

    def _validate_pattern(self, constraint) -> ValidationResult:
        """Validate pattern constraint: column matches regex."""
        table, column = self._parse_attr(constraint.attr)
        pattern = constraint.regex

        if table not in self.tables:
            return ValidationResult(
                name=f"{table}.{column}.pattern",
                passed=False,
                message=f"Table {table} not found",
                details={"table": table, "column": column}
            )

        df = self.tables[table]

        if column not in df.columns:
            return ValidationResult(
                name=f"{table}.{column}.pattern",
                passed=False,
                message=f"Column {column} not found for pattern validation",
                details={"table": table, "column": column}
            )

        col_data = df[column].dropna().astype(str)
        total = len(col_data)

        try:
            regex = re.compile(pattern)
            matches = col_data.str.match(regex).sum()
            violations = total - matches
            passed = violations == 0

            return ValidationResult(
                name=f"{table}.{column}.pattern",
                passed=passed,
                message=f"Pattern /{pattern}/: {matches}/{total} matches",
                details={
                    "table": table,
                    "column": column,
                    "pattern": pattern,
                    "total_values": int(total),
                    "matches": int(matches),
                    "violations": int(violations)
                }
            )
        except re.error as e:
            return ValidationResult(
                name=f"{table}.{column}.pattern",
                passed=False,
                message=f"Invalid regex pattern: {e}",
                details={
                    "table": table,
                    "column": column,
                    "pattern": pattern,
                    "error": str(e)
                }
            )

    def _validate_enum(self, constraint) -> ValidationResult:
        """Validate enum constraint: column values in allowed set."""
        table, column = self._parse_attr(constraint.attr)

        if table not in self.tables:
            return ValidationResult(
                name=f"{table}.{column}.enum",
                passed=False,
                message=f"Table {table} not found",
                details={"table": table, "column": column}
            )

        df = self.tables[table]

        if column not in df.columns:
            return ValidationResult(
                name=f"{table}.{column}.enum",
                passed=False,
                message=f"Column {column} not found for enum validation",
                details={"table": table, "column": column}
            )

        col_data = df[column].dropna()
        total = len(col_data)

        # Get allowed values from either values or enum_ref
        if constraint.values:
            allowed = constraint.values
        elif constraint.enum_ref:
            # TODO: resolve enum_ref (for MVP, skip)
            return ValidationResult(
                name=f"{table}.{column}.enum",
                passed=False,
                message=f"enum_ref not yet supported",
                details={"table": table, "column": column, "enum_ref": constraint.enum_ref}
            )
        else:
            return ValidationResult(
                name=f"{table}.{column}.enum",
                passed=False,
                message=f"No values or enum_ref specified",
                details={"table": table, "column": column}
            )

        allowed_set = set(allowed)
        violations = (~col_data.isin(allowed_set)).sum()
        valid_count = total - violations
        passed = violations == 0

        return ValidationResult(
            name=f"{table}.{column}.enum",
            passed=passed,
            message=f"Enum validation: {valid_count}/{total} values in allowed set",
            details={
                "table": table,
                "column": column,
                "allowed_values": allowed,
                "total_values": int(total),
                "valid_values": int(valid_count),
                "violations": int(violations),
                "unique_actual": list(col_data.unique()[:10])  # Sample
            }
        )

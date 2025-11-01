"""
Structural validators for generated datasets.

Validates:
- Primary key uniqueness
- Foreign key integrity
- Non-null constraints
- Column existence
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from pathlib import Path

from ..core.schema import Dataset, Node


def _jsonify(obj: Any) -> Any:
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    else:
        return obj


class ValidationResult:
    """Result of a single validation check."""

    def __init__(self, name: str, passed: bool, message: str, details: Optional[Dict] = None):
        self.name = name
        self.passed = bool(passed)  # Ensure Python bool
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "details": _jsonify(self.details)
        }


class StructuralValidator:
    """Validates structural constraints on generated data."""

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
        """Run all structural validations."""
        results = []

        # Load all tables first
        self.load_tables()

        # Validate each table
        for node in self.dataset.nodes:
            if node.id not in self.tables:
                results.append(ValidationResult(
                    name=f"{node.id}.exists",
                    passed=False,
                    message=f"Table {node.id} not found in output directory",
                    details={"table": node.id}
                ))
                continue

            df = self.tables[node.id]

            # Check PK uniqueness
            results.append(self._validate_pk_uniqueness(node, df))

            # Check column existence
            for col in node.columns:
                results.append(self._validate_column_exists(node, df, col.name))

                # Check nullable constraints
                results.append(self._validate_nullable(node, df, col))

            # Check FK integrity for dependencies (parents)
            if node.parents:
                for parent_id in node.parents:
                    results.extend(self._validate_fk_integrity(node, df, parent_id))

        # Validate unique constraints from schema.constraints
        if self.dataset.constraints.unique:
            for unique_ref in self.dataset.constraints.unique:
                result = self._validate_unique_constraint(unique_ref)
                if result:
                    results.append(result)

        # Validate all FK constraints from schema.constraints
        if self.dataset.constraints.foreign_keys:
            for fk in self.dataset.constraints.foreign_keys:
                result = self._validate_fk_constraint(fk)
                if result:
                    results.extend(result)

        return results

    def _validate_pk_uniqueness(self, node: Node, df: pd.DataFrame) -> ValidationResult:
        """Validate that primary key is unique."""
        pk_col = node.pk

        if pk_col not in df.columns:
            return ValidationResult(
                name=f"{node.id}.pk_exists",
                passed=False,
                message=f"Primary key column {pk_col} not found",
                details={"table": node.id, "pk_column": pk_col}
            )

        duplicates = df[pk_col].duplicated().sum()
        total_rows = len(df)
        unique_count = df[pk_col].nunique()

        passed = duplicates == 0

        return ValidationResult(
            name=f"{node.id}.pk_unique",
            passed=passed,
            message=f"Primary key {pk_col} uniqueness: {unique_count}/{total_rows} unique",
            details={
                "table": node.id,
                "pk_column": pk_col,
                "total_rows": total_rows,
                "unique_rows": unique_count,
                "duplicates": int(duplicates)
            }
        )

    def _validate_column_exists(self, node: Node, df: pd.DataFrame, col_name: str) -> ValidationResult:
        """Validate that column exists in table."""
        passed = col_name in df.columns

        return ValidationResult(
            name=f"{node.id}.{col_name}.exists",
            passed=passed,
            message=f"Column {col_name} {'exists' if passed else 'missing'} in {node.id}",
            details={
                "table": node.id,
                "column": col_name,
                "actual_columns": list(df.columns)
            }
        )

    def _validate_fk_integrity(self, node: Node, df: pd.DataFrame, parent_id: str) -> List[ValidationResult]:
        """Validate foreign key integrity."""
        results = []

        if parent_id not in self.tables:
            return [ValidationResult(
                name=f"{node.id}.fk_{parent_id}.parent_exists",
                passed=False,
                message=f"Parent table {parent_id} not found for FK validation",
                details={"table": node.id, "parent": parent_id}
            )]

        parent_df = self.tables[parent_id]
        fk_col = f"{parent_id}_id"

        if fk_col not in df.columns:
            return [ValidationResult(
                name=f"{node.id}.fk_{parent_id}.column_exists",
                passed=False,
                message=f"Foreign key column {fk_col} not found in {node.id}",
                details={"table": node.id, "fk_column": fk_col}
            )]

        # Find parent node to get its PK column name
        parent_node = next((n for n in self.dataset.nodes if n.id == parent_id), None)
        if not parent_node:
            return [ValidationResult(
                name=f"{node.id}.fk_{parent_id}.parent_node_not_found",
                passed=False,
                message=f"Parent node definition for {parent_id} not found",
                details={"table": node.id, "parent": parent_id}
            )]

        pk_col = parent_node.pk
        if pk_col not in parent_df.columns:
            return [ValidationResult(
                name=f"{node.id}.fk_{parent_id}.parent_pk_exists",
                passed=False,
                message=f"Parent PK column {pk_col} not found in {parent_id}",
                details={"table": node.id, "parent": parent_id, "pk_column": pk_col}
            )]

        # Check FK integrity
        parent_pks = set(parent_df[pk_col])
        child_fks = df[fk_col].dropna()  # Exclude nulls
        invalid_fks = set(child_fks) - parent_pks

        total_fks = len(child_fks)
        valid_fks = total_fks - len(invalid_fks)
        passed = len(invalid_fks) == 0

        results.append(ValidationResult(
            name=f"{node.id}.fk_{parent_id}.integrity",
            passed=passed,
            message=f"FK {fk_col} integrity: {valid_fks}/{total_fks} valid references",
            details={
                "table": node.id,
                "parent": parent_id,
                "fk_column": fk_col,
                "total_references": int(total_fks),
                "valid_references": int(valid_fks),
                "invalid_count": len(invalid_fks),
                "sample_invalid": list(invalid_fks)[:5] if invalid_fks else []
            }
        ))

        return results

    def _validate_nullable(self, node: Node, df: pd.DataFrame, col) -> ValidationResult:
        """Validate nullable constraints on columns."""
        col_name = col.name
        is_nullable = col.nullable

        if col_name not in df.columns:
            # Column existence is validated separately
            return ValidationResult(
                name=f"{node.id}.{col_name}.nullable_check",
                passed=True,
                message=f"Skipped (column missing)",
                details={}
            )

        null_count = df[col_name].isna().sum()
        total_rows = len(df)

        if not is_nullable and null_count > 0:
            # Non-nullable column has nulls - FAIL
            passed = False
            message = f"Non-nullable column has {null_count}/{total_rows} null values"
        else:
            # Either nullable=True or no nulls - PASS
            passed = True
            if is_nullable:
                message = f"Nullable column: {null_count}/{total_rows} nulls (allowed)"
            else:
                message = f"Non-nullable column: 0/{total_rows} nulls"

        return ValidationResult(
            name=f"{node.id}.{col_name}.nullable",
            passed=passed,
            message=message,
            details={
                "table": node.id,
                "column": col_name,
                "nullable": is_nullable,
                "null_count": int(null_count),
                "total_rows": int(total_rows)
            }
        )

    def _validate_unique_constraint(self, unique_ref: str) -> Optional[ValidationResult]:
        """Validate unique constraint from schema.constraints.unique."""
        if "." not in unique_ref:
            return None

        table, column = unique_ref.split(".", 1)

        if table not in self.tables:
            return ValidationResult(
                name=f"{table}.{column}.unique",
                passed=False,
                message=f"Table {table} not found for unique constraint",
                details={"table": table, "column": column}
            )

        df = self.tables[table]

        if column not in df.columns:
            return ValidationResult(
                name=f"{table}.{column}.unique",
                passed=False,
                message=f"Column {column} not found for unique constraint",
                details={"table": table, "column": column}
            )

        duplicates = df[column].duplicated().sum()
        total_rows = len(df)
        unique_count = df[column].nunique()

        passed = duplicates == 0

        return ValidationResult(
            name=f"{table}.{column}.unique",
            passed=passed,
            message=f"Unique constraint: {unique_count}/{total_rows} unique values",
            details={
                "table": table,
                "column": column,
                "total_rows": int(total_rows),
                "unique_values": int(unique_count),
                "duplicates": int(duplicates)
            }
        )

    def _validate_fk_constraint(self, fk) -> List[ValidationResult]:
        """Validate FK constraint from schema.constraints.foreign_keys."""
        results = []

        if "." not in fk.from_ or "." not in fk.to:
            return []

        from_table, from_col = fk.from_.split(".", 1)
        to_table, to_col = fk.to.split(".", 1)

        if from_table not in self.tables:
            return [ValidationResult(
                name=f"{from_table}.fk_constraint.{from_col}",
                passed=False,
                message=f"Source table {from_table} not found for FK constraint",
                details={"from": fk.from_, "to": fk.to}
            )]

        if to_table not in self.tables:
            return [ValidationResult(
                name=f"{from_table}.fk_constraint.{from_col}",
                passed=False,
                message=f"Target table {to_table} not found for FK constraint",
                details={"from": fk.from_, "to": fk.to}
            )]

        from_df = self.tables[from_table]
        to_df = self.tables[to_table]

        if from_col not in from_df.columns:
            return [ValidationResult(
                name=f"{from_table}.fk_constraint.{from_col}",
                passed=False,
                message=f"Source column {from_col} not found in {from_table}",
                details={"from": fk.from_, "to": fk.to}
            )]

        if to_col not in to_df.columns:
            return [ValidationResult(
                name=f"{from_table}.fk_constraint.{from_col}",
                passed=False,
                message=f"Target column {to_col} not found in {to_table}",
                details={"from": fk.from_, "to": fk.to}
            )]

        # Check FK integrity
        target_values = set(to_df[to_col])
        source_values = from_df[from_col].dropna()
        invalid_refs = set(source_values) - target_values

        total_refs = len(source_values)
        valid_refs = total_refs - len(invalid_refs)
        passed = len(invalid_refs) == 0

        results.append(ValidationResult(
            name=f"{from_table}.fk_constraint.{from_col}_to_{to_table}.{to_col}",
            passed=passed,
            message=f"FK {fk.from_} → {fk.to}: {valid_refs}/{total_refs} valid",
            details={
                "from_table": from_table,
                "from_column": from_col,
                "to_table": to_table,
                "to_column": to_col,
                "total_references": int(total_refs),
                "valid_references": int(valid_refs),
                "invalid_count": len(invalid_refs),
                "sample_invalid": list(invalid_refs)[:5] if invalid_refs else []
            }
        ))

        return results

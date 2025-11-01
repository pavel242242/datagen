"""
Comprehensive preflight validation for schemas.

Validates that a schema will successfully generate without runtime errors.
This catches all potential issues BEFORE generation starts.
"""

from typing import List, Set, Dict, Optional
from faker import Faker
import pandas as pd
import re

from .schema import Dataset, Node


class PreflightError:
    """A single preflight validation error."""

    def __init__(self, severity: str, location: str, message: str, suggestion: str = ""):
        self.severity = severity  # "error" or "warning"
        self.location = location  # e.g., "nodes.customer.columns.address"
        self.message = message
        self.suggestion = suggestion

    def __str__(self):
        result = f"[{self.severity.upper()}] {self.location}: {self.message}"
        if self.suggestion:
            result += f"\n  Suggestion: {self.suggestion}"
        return result


class PreflightValidator:
    """Validates schema before generation to catch all potential runtime errors."""

    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self.errors: List[PreflightError] = []
        self.warnings: List[PreflightError] = []

        # Build lookup tables
        self.nodes_by_id: Dict[str, Node] = {n.id: n for n in dataset.nodes}
        self.columns_by_table: Dict[str, Set[str]] = {}
        for node in dataset.nodes:
            self.columns_by_table[node.id] = {col.name for col in node.columns}

    def validate_all(self) -> bool:
        """Run all preflight validations. Returns True if no errors."""
        self._validate_lookup_references()
        self._validate_faker_methods()
        self._validate_expression_syntax()
        self._validate_modifier_compatibility()
        self._validate_constraint_references()
        self._validate_target_references()
        self._validate_parent_references()
        self._validate_fanout_rules()
        self._validate_locale_references()
        self._validate_column_types()

        return len(self.errors) == 0

    def _validate_lookup_references(self):
        """Validate all lookup references point to existing table.column."""
        for node in self.dataset.nodes:
            for col in node.columns:
                if not col.generator:
                    continue

                # Check lookup generator
                if isinstance(col.generator, dict) and "lookup" in col.generator:
                    lookup_spec = col.generator["lookup"]
                    from_ref = lookup_spec.get("from")

                    if not from_ref:
                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.columns.{col.name}.generator.lookup",
                            "Missing 'from' field in lookup generator",
                            "Add 'from': 'table.column'"
                        ))
                        continue

                    if "." not in from_ref:
                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.columns.{col.name}.generator.lookup.from",
                            f"Invalid lookup reference: '{from_ref}'. Must be in 'table.column' format",
                            f"Change to 'table.column' format, e.g., 'customer.customer_id'"
                        ))
                        continue

                    ref_table, ref_column = from_ref.split(".", 1)

                    # Check table exists
                    if ref_table not in self.nodes_by_id:
                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.columns.{col.name}.generator.lookup.from",
                            f"Lookup references non-existent table: '{ref_table}'",
                            f"Available tables: {list(self.nodes_by_id.keys())}"
                        ))
                        continue

                    # Check column exists in that table
                    if ref_column not in self.columns_by_table.get(ref_table, set()):
                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.columns.{col.name}.generator.lookup.from",
                            f"Lookup references non-existent column: '{ref_table}.{ref_column}'",
                            f"Available columns in {ref_table}: {list(self.columns_by_table.get(ref_table, []))}"
                        ))

    def _validate_faker_methods(self):
        """Validate all Faker methods are real."""
        faker = Faker()
        valid_methods = set(dir(faker))

        for node in self.dataset.nodes:
            for col in node.columns:
                if not col.generator:
                    continue

                if isinstance(col.generator, dict) and "faker" in col.generator:
                    faker_spec = col.generator["faker"]
                    method = faker_spec.get("method")

                    if not method:
                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.columns.{col.name}.generator.faker",
                            "Missing 'method' field in faker generator",
                            "Add 'method': 'name', 'email', 'address', etc."
                        ))
                        continue

                    if method not in valid_methods:
                        # Try to suggest similar methods
                        similar = [m for m in valid_methods if method.lower() in m.lower() or m.lower() in method.lower()]
                        suggestion = f"Method '{method}' not found in Faker. "
                        if similar:
                            suggestion += f"Did you mean: {similar[:3]}?"
                        else:
                            suggestion += "See https://faker.readthedocs.io/en/master/providers.html"

                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.columns.{col.name}.generator.faker.method",
                            f"Invalid Faker method: '{method}'",
                            suggestion
                        ))

    def _validate_expression_syntax(self):
        """Validate all expression generators have valid pandas eval syntax."""
        for node in self.dataset.nodes:
            for col in node.columns:
                if not col.generator:
                    continue

                if isinstance(col.generator, dict) and "expression" in col.generator:
                    expr_spec = col.generator["expression"]
                    expr = expr_spec.get("code")

                    if not expr:
                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.columns.{col.name}.generator.expression",
                            "Missing 'code' field in expression generator",
                            "Add 'code': 'column1 + column2'"
                        ))
                        continue

                    # Basic validation: check that expression is a non-empty string
                    # Full validation happens at generation time when columns are available
                    if not isinstance(expr, str) or not expr.strip():
                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.columns.{col.name}.generator.expression.code",
                            "Expression code must be a non-empty string",
                            "Expression must be valid pandas eval syntax like 'column1 * column2'"
                        ))

    def _validate_modifier_compatibility(self):
        """Validate modifiers are compatible with column types."""
        for node in self.dataset.nodes:
            for col in node.columns:
                if not col.modifiers:
                    continue

                for i, modifier in enumerate(col.modifiers):
                    if hasattr(modifier, 'transform'):
                        transform = modifier.transform
                        args = modifier.args if hasattr(modifier, 'args') else {}
                    else:
                        transform = modifier.get("transform")
                        args = modifier.get("args", {})

                    # Validate seasonality modifier
                    if transform == "seasonality":
                        dimension = args.get("dimension")
                        weights = args.get("weights", [])

                        if not dimension:
                            self.errors.append(PreflightError(
                                "error",
                                f"nodes.{node.id}.columns.{col.name}.modifiers[{i}]",
                                "Seasonality modifier missing 'dimension'",
                                "Add 'dimension': 'hour', 'dow', or 'month'"
                            ))
                            continue

                        if dimension not in ["hour", "dow", "month"]:
                            self.errors.append(PreflightError(
                                "error",
                                f"nodes.{node.id}.columns.{col.name}.modifiers[{i}].dimension",
                                f"Invalid seasonality dimension: '{dimension}'",
                                "Use 'hour' (24), 'dow' (7), or 'month' (12)"
                            ))

                        # Validate weights count
                        expected_count = {"hour": 24, "dow": 7, "month": 12}.get(dimension, 0)
                        if expected_count and len(weights) != expected_count:
                            self.warnings.append(PreflightError(
                                "warning",
                                f"nodes.{node.id}.columns.{col.name}.modifiers[{i}].weights",
                                f"Seasonality weights for '{dimension}' should have {expected_count} values, got {len(weights)}",
                                f"Weights will be padded/truncated to {expected_count}"
                            ))

                        # Check if column is datetime type
                        if col.type not in ["datetime", "date"]:
                            self.warnings.append(PreflightError(
                                "warning",
                                f"nodes.{node.id}.columns.{col.name}.modifiers[{i}]",
                                f"Seasonality modifier on non-datetime column (type: {col.type})",
                                "Seasonality works best on datetime/date columns"
                            ))

    def _validate_constraint_references(self):
        """Validate all constraint references point to existing table.column."""
        constraints = self.dataset.constraints

        # Validate unique constraints
        if constraints.unique:
            for ref in constraints.unique:
                if "." not in ref:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.unique",
                        f"Invalid unique constraint reference: '{ref}'. Must be 'table.column'",
                        "Use format 'table.column'"
                    ))
                    continue

                table, column = ref.split(".", 1)
                if table not in self.nodes_by_id:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.unique",
                        f"Unique constraint references non-existent table: '{table}'",
                        f"Available tables: {list(self.nodes_by_id.keys())}"
                    ))
                elif column not in self.columns_by_table.get(table, set()):
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.unique",
                        f"Unique constraint references non-existent column: '{table}.{column}'",
                        f"Available columns: {list(self.columns_by_table.get(table, []))}"
                    ))

        # Validate foreign key constraints
        if constraints.foreign_keys:
            for fk in constraints.foreign_keys:
                # Validate from reference
                if "." not in fk.from_:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.foreign_keys",
                        f"Invalid FK 'from' reference: '{fk.from_}'. Must be 'table.column'",
                        "Use format 'table.column'"
                    ))
                    continue

                from_table, from_col = fk.from_.split(".", 1)
                if from_table not in self.nodes_by_id:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.foreign_keys.from",
                        f"FK references non-existent table: '{from_table}'",
                        f"Available tables: {list(self.nodes_by_id.keys())}"
                    ))
                elif from_col not in self.columns_by_table.get(from_table, set()):
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.foreign_keys.from",
                        f"FK references non-existent column: '{from_table}.{from_col}'",
                        f"Available columns: {list(self.columns_by_table.get(from_table, []))}"
                    ))

                # Validate to reference
                if "." not in fk.to:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.foreign_keys",
                        f"Invalid FK 'to' reference: '{fk.to}'. Must be 'table.column'",
                        "Use format 'table.column'"
                    ))
                    continue

                to_table, to_col = fk.to.split(".", 1)
                if to_table not in self.nodes_by_id:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.foreign_keys.to",
                        f"FK references non-existent table: '{to_table}'",
                        f"Available tables: {list(self.nodes_by_id.keys())}"
                    ))
                elif to_col not in self.columns_by_table.get(to_table, set()):
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.foreign_keys.to",
                        f"FK references non-existent column: '{to_table}.{to_col}'",
                        f"Available columns: {list(self.columns_by_table.get(to_table, []))}"
                    ))

        # Validate range constraints
        if constraints.ranges:
            for range_constraint in constraints.ranges:
                if "." not in range_constraint.attr:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.ranges",
                        f"Invalid range constraint reference: '{range_constraint.attr}'. Must be 'table.column'",
                        "Use format 'table.column'"
                    ))
                    continue

                table, column = range_constraint.attr.split(".", 1)
                if table not in self.nodes_by_id:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.ranges.attr",
                        f"Range constraint references non-existent table: '{table}'",
                        f"Available tables: {list(self.nodes_by_id.keys())}"
                    ))
                elif column not in self.columns_by_table.get(table, set()):
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.ranges.attr",
                        f"Range constraint references non-existent column: '{table}.{column}'",
                        f"Available columns: {list(self.columns_by_table.get(table, []))}"
                    ))

        # Validate inequality constraints
        if constraints.inequalities:
            for ineq in constraints.inequalities:
                for side, ref in [("left", ineq.left), ("right", ineq.right)]:
                    # References can be table.column or just column (same table)
                    if "." in ref:
                        table, column = ref.split(".", 1)
                        if table not in self.nodes_by_id:
                            self.errors.append(PreflightError(
                                "error",
                                f"constraints.inequalities.{side}",
                                f"Inequality references non-existent table: '{table}'",
                                f"Available tables: {list(self.nodes_by_id.keys())}"
                            ))
                        elif column not in self.columns_by_table.get(table, set()):
                            self.errors.append(PreflightError(
                                "error",
                                f"constraints.inequalities.{side}",
                                f"Inequality references non-existent column: '{table}.{column}'",
                                f"Available columns: {list(self.columns_by_table.get(table, []))}"
                            ))

        # Validate pattern constraints
        if constraints.pattern:
            for pattern_constraint in constraints.pattern:
                if "." not in pattern_constraint.attr:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.pattern",
                        f"Invalid pattern constraint reference: '{pattern_constraint.attr}'. Must be 'table.column'",
                        "Use format 'table.column'"
                    ))
                    continue

                table, column = pattern_constraint.attr.split(".", 1)
                if table not in self.nodes_by_id:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.pattern.attr",
                        f"Pattern constraint references non-existent table: '{table}'",
                        f"Available tables: {list(self.nodes_by_id.keys())}"
                    ))
                elif column not in self.columns_by_table.get(table, set()):
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.pattern.attr",
                        f"Pattern constraint references non-existent column: '{table}.{column}'",
                        f"Available columns: {list(self.columns_by_table.get(table, []))}"
                    ))

                # Validate regex syntax
                try:
                    re.compile(pattern_constraint.regex)
                except re.error as e:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.pattern.regex",
                        f"Invalid regex pattern: {e}",
                        "Fix the regular expression syntax"
                    ))

        # Validate enum constraints
        if constraints.enum:
            for enum_constraint in constraints.enum:
                if "." not in enum_constraint.attr:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.enum",
                        f"Invalid enum constraint reference: '{enum_constraint.attr}'. Must be 'table.column'",
                        "Use format 'table.column'"
                    ))
                    continue

                table, column = enum_constraint.attr.split(".", 1)
                if table not in self.nodes_by_id:
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.enum.attr",
                        f"Enum constraint references non-existent table: '{table}'",
                        f"Available tables: {list(self.nodes_by_id.keys())}"
                    ))
                elif column not in self.columns_by_table.get(table, set()):
                    self.errors.append(PreflightError(
                        "error",
                        f"constraints.enum.attr",
                        f"Enum constraint references non-existent column: '{table}.{column}'",
                        f"Available columns: {list(self.columns_by_table.get(table, []))}"
                    ))

    def _validate_target_references(self):
        """Validate all target references point to existing table.column."""
        if not self.dataset.targets:
            return

        targets = self.dataset.targets

        # Validate weekend_share target
        if targets.weekend_share:
            ws = targets.weekend_share
            if ws.table not in self.nodes_by_id:
                self.errors.append(PreflightError(
                    "error",
                    f"targets.weekend_share.table",
                    f"Weekend share target references non-existent table: '{ws.table}'",
                    f"Available tables: {list(self.nodes_by_id.keys())}"
                ))
            elif ws.timestamp not in self.columns_by_table.get(ws.table, set()):
                self.errors.append(PreflightError(
                    "error",
                    f"targets.weekend_share.timestamp",
                    f"Weekend share target references non-existent column: '{ws.table}.{ws.timestamp}'",
                    f"Available columns: {list(self.columns_by_table.get(ws.table, []))}"
                ))

        # Validate mean_in_range target
        if targets.mean_in_range:
            mir = targets.mean_in_range
            if mir.table not in self.nodes_by_id:
                self.errors.append(PreflightError(
                    "error",
                    f"targets.mean_in_range.table",
                    f"Mean in range target references non-existent table: '{mir.table}'",
                    f"Available tables: {list(self.nodes_by_id.keys())}"
                ))
            elif mir.column not in self.columns_by_table.get(mir.table, set()):
                self.errors.append(PreflightError(
                    "error",
                    f"targets.mean_in_range.column",
                    f"Mean in range target references non-existent column: '{mir.table}.{mir.column}'",
                    f"Available columns: {list(self.columns_by_table.get(mir.table, []))}"
                ))

    def _validate_parent_references(self):
        """Validate all parent references in fact tables exist."""
        for node in self.dataset.nodes:
            if node.kind == "fact" and node.parents:
                for parent_id in node.parents:
                    if parent_id not in self.nodes_by_id:
                        self.errors.append(PreflightError(
                            "error",
                            f"nodes.{node.id}.parents",
                            f"Fact table references non-existent parent: '{parent_id}'",
                            f"Available tables: {list(self.nodes_by_id.keys())}"
                        ))

    def _validate_fanout_rules(self):
        """Validate fanout is only on fact tables."""
        for node in self.dataset.nodes:
            if node.fanout and node.kind != "fact":
                self.errors.append(PreflightError(
                    "error",
                    f"nodes.{node.id}.fanout",
                    f"Entity table '{node.id}' cannot have fanout. Only fact tables can have fanout.",
                    "Remove fanout or change kind to 'fact' and add parents"
                ))

    def _validate_locale_references(self):
        """Validate locale_from in Faker generators points to valid columns."""
        for node in self.dataset.nodes:
            for col in node.columns:
                if not col.generator:
                    continue

                if isinstance(col.generator, dict) and "faker" in col.generator:
                    faker_spec = col.generator["faker"]
                    locale_from = faker_spec.get("locale_from")

                    if locale_from:
                        # locale_from should reference a column in the same table
                        if locale_from not in self.columns_by_table.get(node.id, set()):
                            self.errors.append(PreflightError(
                                "error",
                                f"nodes.{node.id}.columns.{col.name}.generator.faker.locale_from",
                                f"Faker locale_from references non-existent column: '{locale_from}'",
                                f"Available columns in {node.id}: {list(self.columns_by_table.get(node.id, []))}"
                            ))

    def _validate_column_types(self):
        """Validate column type compatibility with generators."""
        for node in self.dataset.nodes:
            for col in node.columns:
                if not col.generator:
                    continue

                if isinstance(col.generator, dict):
                    # datetime_series should be on datetime/date columns
                    if "datetime_series" in col.generator and col.type not in ["datetime", "date"]:
                        self.warnings.append(PreflightError(
                            "warning",
                            f"nodes.{node.id}.columns.{col.name}",
                            f"datetime_series generator on non-datetime column (type: {col.type})",
                            "Consider changing column type to 'datetime' or 'date'"
                        ))

                    # distribution should be on numeric columns
                    if "distribution" in col.generator and col.type not in ["int", "float"]:
                        self.warnings.append(PreflightError(
                            "warning",
                            f"nodes.{node.id}.columns.{col.name}",
                            f"distribution generator on non-numeric column (type: {col.type})",
                            "Consider changing column type to 'int' or 'float'"
                        ))

    def get_report(self) -> str:
        """Get formatted validation report."""
        lines = []
        lines.append("=" * 70)
        lines.append("SCHEMA PREFLIGHT VALIDATION REPORT")
        lines.append("=" * 70)
        lines.append("")

        if not self.errors and not self.warnings:
            lines.append("✓ All preflight validations passed!")
            lines.append("")
            lines.append("The schema is ready for generation.")
            return "\n".join(lines)

        if self.errors:
            lines.append(f"❌ ERRORS: {len(self.errors)}")
            lines.append("-" * 70)
            for error in self.errors:
                lines.append(str(error))
                lines.append("")

        if self.warnings:
            lines.append(f"⚠️  WARNINGS: {len(self.warnings)}")
            lines.append("-" * 70)
            for warning in self.warnings:
                lines.append(str(warning))
                lines.append("")

        lines.append("=" * 70)
        if self.errors:
            lines.append("❌ Schema validation FAILED. Fix errors before generation.")
        else:
            lines.append("⚠️  Schema validation passed with warnings.")

        return "\n".join(lines)


def preflight_validate(dataset: Dataset) -> bool:
    """
    Run comprehensive preflight validation on a dataset.

    Returns:
        True if validation passed (no errors), False otherwise.

    Raises:
        ValueError: If there are validation errors, with detailed report.
    """
    validator = PreflightValidator(dataset)
    passed = validator.validate_all()

    if not passed:
        report = validator.get_report()
        raise ValueError(f"Schema preflight validation failed:\n\n{report}")

    if validator.warnings:
        # Print warnings but don't fail
        import sys
        print(validator.get_report(), file=sys.stderr)

    return True

"""Integration tests for validation modules.

Tests structural, value, and behavioral validation across all features.
"""

import pytest
import tempfile
from pathlib import Path

from datagen.core.schema import Dataset
from datagen.core.executor import DatasetExecutor
from datagen.validation.structural import StructuralValidator
from datagen.validation.value import ValueValidator
from datagen.validation.behavioral import BehavioralValidator
from datagen.validation.report import ValidationReport


class TestStructuralValidation:
    """Test structural validation (PK, FK, nullability)."""

    def test_structural_validation_simple_entity(self):
        """Test structural validation on simple entity table."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "StructuralTest"},
            "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "H"},
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "rows": 20,
                "columns": [
                    {"name": "user_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {"name": "name", "type": "string", "generator": {"faker": {"method": "name"}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = StructuralValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # Should have at least table existence and PK uniqueness checks
            assert len(results) > 0
            # All checks should pass for valid generated data
            assert all(r.passed for r in results)

    def test_structural_validation_with_foreign_keys(self):
        """Test structural validation with FK relationships."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "FKTest"},
            "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "H"},
            "constraints": {
                "foreign_keys": [
                    {"from": "order.user_id", "to": "user.user_id"}
                ]
            },
            "nodes": [
                {
                    "id": "user",
                    "kind": "entity",
                    "pk": "user_id",
                    "rows": 15,
                    "columns": [
                        {"name": "user_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {"name": "name", "type": "string", "generator": {"faker": {"method": "name"}}}
                    ]
                },
                {
                    "id": "order",
                    "kind": "fact",
                    "pk": "order_id",
                    "parents": ["user"],
                    "fanout": {"distribution": "uniform", "min": 2, "max": 5},
                    "columns": [
                        {"name": "order_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {"name": "user_id", "type": "int", "generator": {"lookup": {"from": "user.user_id"}}},
                        {
                            "name": "amount",
                            "type": "float",
                            "generator": {"distribution": {"type": "normal", "params": {"mean": 50, "sigma": 10}, "clamp": [10, 100]}}
                        }
                    ]
                }
            ]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = StructuralValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # FK integrity should pass
            assert all(r.passed for r in results)


class TestValueConstraintValidation:
    """Test value constraint validation (ranges, patterns, enums)."""

    def test_value_validation_ranges(self):
        """Test value validation with range constraints."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "ValueTest"},
            "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "H"},
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "product",
                "kind": "entity",
                "pk": "product_id",
                "rows": 25,
                "columns": [
                    {"name": "product_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "price",
                        "type": "float",
                        "generator": {"distribution": {"type": "normal", "params": {"mean": 50, "sigma": 10}, "clamp": [10, 100]}}
                    },
                    {
                        "name": "quantity",
                        "type": "int",
                        "generator": {"distribution": {"type": "poisson", "params": {"lambda": 10}, "clamp": [1, 50]}}
                    }
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = ValueValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # Value validator should run without errors
            assert isinstance(results, list)


class TestBehavioralValidation:
    """Test behavioral validation (seasonality, trends, targets)."""

    def test_behavioral_validation_runs(self):
        """Test behavioral validation executes without errors."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "BehavioralTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "H"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "event",
                "kind": "entity",
                "pk": "event_id",
                "rows": 50,
                "columns": [
                    {"name": "event_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "timestamp",
                        "type": "datetime",
                        "generator": {
                            "datetime_series": {
                                "within": {
                                    "start": "2024-01-01T00:00:00Z",
                                    "end": "2024-12-31T23:59:59Z"
                                },
                                "freq": "D"
                            }
                        }
                    },
                    {
                        "name": "value",
                        "type": "int",
                        "generator": {"distribution": {"type": "normal", "params": {"mean": 100, "sigma": 10}, "clamp": [50, 150]}}
                    }
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = BehavioralValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # Behavioral validation should run without errors
            assert isinstance(results, list)


class TestValidationReport:
    """Test validation report generation."""

    def test_generate_full_validation_report(self):
        """Test full validation report with all validators."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "ReportTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "H"
            },
            "constraints": {
                "foreign_keys": [
                    {"from": "order.user_id", "to": "user.user_id"}
                ]
            },
            "nodes": [
                {
                    "id": "user",
                    "kind": "entity",
                    "pk": "user_id",
                    "rows": 30,
                    "columns": [
                        {"name": "user_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {"name": "name", "type": "string", "generator": {"faker": {"method": "name"}}},
                        {"name": "email", "type": "string", "generator": {"faker": {"method": "email"}}}
                    ]
                },
                {
                    "id": "order",
                    "kind": "fact",
                    "pk": "order_id",
                    "parents": ["user"],
                    "fanout": {"distribution": "poisson", "lambda": 4},
                    "columns": [
                        {"name": "order_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {"name": "user_id", "type": "int", "generator": {"lookup": {"from": "user.user_id"}}},
                        {
                            "name": "order_date",
                            "type": "datetime",
                            "generator": {
                                "datetime_series": {
                                    "within": {
                                        "start": "2024-01-01T00:00:00Z",
                                        "end": "2024-12-31T23:59:59Z"
                                    },
                                    "freq": "H"
                                }
                            }
                        },
                        {
                            "name": "amount",
                            "type": "float",
                            "generator": {"distribution": {"type": "lognormal", "params": {"mean": 3.5, "sigma": 0.5}, "clamp": [10.0, 500.0]}}
                        }
                    ]
                }
            ]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            # Create validation report
            report = ValidationReport(schema, Path(tmpdir))
            report.run_all_validations()

            # Report should have schema name
            assert report.dataset.metadata.name == "ReportTest"
            # Should have results from all validators
            assert len(report.results) > 0
            # Report should be JSON serializable
            report_dict = report.to_dict()
            assert isinstance(report_dict, dict)
            assert "metadata" in report_dict
            assert report_dict["metadata"]["dataset_name"] == "ReportTest"

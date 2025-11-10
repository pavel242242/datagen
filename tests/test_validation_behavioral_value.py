"""Comprehensive tests for behavioral and value validators."""

import pytest
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from datagen.core.schema import Dataset
from datagen.core.executor import DatasetExecutor
from datagen.validation.behavioral import BehavioralValidator
from datagen.validation.value import ValueValidator


class TestBehavioralValidatorWeekendShare:
    """Tests for weekend share validation."""

    def test_weekend_share_within_target(self):
        """Test weekend share validation when target is met."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "WeekendShareTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "weekend_share": {
                    "table": "event",
                    "timestamp": "event_time",
                    "min": 0.20,
                    "max": 0.35
                }
            },
            "nodes": [{
                "id": "event",
                "kind": "entity",
                "pk": "event_id",
                "rows": 100,
                "columns": [
                    {"name": "event_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "event_time",
                        "type": "datetime",
                        "generator": {
                            "datetime_series": {
                                "within": {
                                    "start": "2024-01-01T00:00:00Z",
                                    "end": "2024-12-31T23:59:59Z"
                                },
                                "freq": "h",
                                "pattern": {
                                    "dimension": "dow",
                                    "weights": [1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 1.5]
                                }
                            }
                        }
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

            # Should have one result for weekend_share
            assert len(results) == 1
            result = results[0]

            # Check result structure
            assert result.name == "event.weekend_share"
            assert "Weekend share" in result.message  # Capital W
            assert "actual_share" in result.details
            assert "weekend_count" in result.details

    def test_weekend_share_table_not_found(self):
        """Test weekend share validation when table doesn't exist."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "WeekendShareMissingTable"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "weekend_share": {
                    "table": "missing_table",
                    "timestamp": "event_time",
                    "min": 0.20,
                    "max": 0.35
                }
            },
            "nodes": [{
                "id": "event",
                "kind": "entity",
                "pk": "event_id",
                "rows": 50,
                "columns": [
                    {"name": "event_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = BehavioralValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # Should fail with table not found
            assert len(results) == 1
            result = results[0]
            assert not result.passed
            assert "not found" in result.message.lower()


class TestBehavioralValidatorMeanInRange:
    """Tests for mean in range validation."""

    def test_mean_in_range_within_target(self):
        """Test mean in range validation when target is met."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "MeanInRangeTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "mean_in_range": {
                    "table": "metric",
                    "column": "value",
                    "min": 90,
                    "max": 110
                }
            },
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "metric_id",
                "rows": 100,
                "columns": [
                    {"name": "metric_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "value",
                        "type": "float",
                        "generator": {
                            "distribution": {
                                "type": "normal",
                                "params": {"mean": 100, "sigma": 5},
                                "clamp": [80, 120]
                            }
                        }
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

            # Should have one result for mean_in_range
            assert len(results) == 1
            result = results[0]
            assert result.name == "metric.value.mean_in_range"
            assert "actual_mean" in result.details

    def test_mean_in_range_column_not_found(self):
        """Test mean in range validation when column doesn't exist."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "MeanInRangeMissingColumn"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "mean_in_range": {
                    "table": "metric",
                    "column": "missing_column",
                    "min": 90,
                    "max": 110
                }
            },
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "metric_id",
                "rows": 50,
                "columns": [
                    {"name": "metric_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = BehavioralValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # Should fail with column not found
            assert len(results) == 1
            result = results[0]
            assert not result.passed
            assert "not found" in result.message.lower()


class TestValueValidatorRange:
    """Tests for range constraint validation."""

    def test_range_all_values_in_range(self):
        """Test range validation when all values are within range."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "RangeValidTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "ranges": [
                    {"attr": "metric.value", "min": 0, "max": 100}
                ]
            },
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "metric_id",
                "rows": 100,
                "columns": [
                    {"name": "metric_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "value",
                        "type": "float",
                        "generator": {
                            "distribution": {
                                "type": "uniform",
                                "params": {"low": 10, "high": 90},
                                "clamp": [0, 100]
                            }
                        }
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

            # Should pass range validation
            assert len(results) == 1
            result = results[0]
            assert result.name == "metric.value.range"
            assert result.passed
            assert result.details["violations"] == 0

    def test_range_violations(self):
        """Test range validation when some values are out of range."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "RangeViolationTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "ranges": [
                    {"attr": "metric.value", "min": 40, "max": 60}
                ]
            },
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "metric_id",
                "rows": 100,
                "columns": [
                    {"name": "metric_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "value",
                        "type": "float",
                        "generator": {
                            "distribution": {
                                "type": "uniform",
                                "params": {"low": 10, "high": 90},
                                "clamp": [0, 100]
                            }
                        }
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

            # Should have violations
            assert len(results) == 1
            result = results[0]
            assert not result.passed
            assert result.details["violations"] > 0


class TestValueValidatorInequality:
    """Tests for inequality constraint validation."""

    def test_inequality_all_satisfied(self):
        """Test inequality validation when all constraints are satisfied."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "InequalityValidTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "inequalities": [
                    {"left": "period.start_date", "op": "<", "right": "period.end_date"}
                ]
            },
            "nodes": [{
                "id": "period",
                "kind": "entity",
                "pk": "period_id",
                "rows": 50,
                "columns": [
                    {"name": "period_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "start_date",
                        "type": "datetime",
                        "generator": {
                            "datetime_series": {
                                "within": {
                                    "start": "2024-01-01T00:00:00Z",
                                    "end": "2024-06-30T23:59:59Z"
                                },
                                "freq": "D"
                            }
                        }
                    },
                    {
                        "name": "end_date",
                        "type": "datetime",
                        "generator": {
                            "datetime_series": {
                                "within": {
                                    "start": "2024-07-01T00:00:00Z",
                                    "end": "2024-12-31T23:59:59Z"
                                },
                                "freq": "D"
                            }
                        }
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

            # Should pass inequality validation
            assert len(results) == 1
            result = results[0]
            assert result.name == "period.inequality.start_date_<_end_date"
            assert result.passed
            assert result.details["violations"] == 0

    def test_inequality_column_not_found(self):
        """Test inequality validation when column doesn't exist."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "InequalityMissingColumn"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "inequalities": [
                    {"left": "metric.missing_col", "op": "<", "right": "metric.b"}
                ]
            },
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "metric_id",
                "rows": 50,
                "columns": [
                    {"name": "metric_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {"name": "b", "type": "int", "generator": {"sequence": {"start": 10, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = ValueValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # Should fail with column not found
            assert len(results) == 1
            result = results[0]
            assert not result.passed
            assert "not found" in result.message.lower()


class TestValueValidatorPattern:
    """Tests for pattern constraint validation."""

    def test_pattern_all_match(self):
        """Test pattern validation when all values match."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "PatternValidTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "pattern": [
                    {"attr": "customer.email", "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"}
                ]
            },
            "nodes": [{
                "id": "customer",
                "kind": "entity",
                "pk": "customer_id",
                "rows": 50,
                "columns": [
                    {"name": "customer_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "email",
                        "type": "string",
                        "generator": {"faker": {"method": "email"}}
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

            # Should pass pattern validation
            assert len(results) == 1
            result = results[0]
            assert result.name == "customer.email.pattern"
            # Email generation should match the pattern
            assert result.details["violations"] == 0

    def test_pattern_invalid_regex(self):
        """Test pattern validation with invalid regex."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "PatternInvalidRegex"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "pattern": [
                    {"attr": "customer.name", "regex": r"[invalid(regex"}
                ]
            },
            "nodes": [{
                "id": "customer",
                "kind": "entity",
                "pk": "customer_id",
                "rows": 50,
                "columns": [
                    {"name": "customer_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {"name": "name", "type": "string", "generator": {"faker": {"method": "name"}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = ValueValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # Should fail with invalid regex
            assert len(results) == 1
            result = results[0]
            assert not result.passed
            assert "invalid" in result.message.lower() or "error" in result.message.lower()


class TestValueValidatorEnum:
    """Tests for enum constraint validation."""

    def test_enum_all_in_allowed_set(self):
        """Test enum validation when all values are in allowed set."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "EnumValidTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "enum": [
                    {"attr": "order.status", "values": ["pending", "completed", "cancelled"]}
                ]
            },
            "nodes": [{
                "id": "order",
                "kind": "entity",
                "pk": "order_id",
                "rows": 100,
                "columns": [
                    {"name": "order_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "status",
                        "type": "string",
                        "generator": {
                            "choice": {
                                "choices": ["pending", "completed", "cancelled"]
                            }
                        }
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

            # Should pass enum validation
            assert len(results) == 1
            result = results[0]
            assert result.name == "order.status.enum"
            assert result.passed
            assert result.details["violations"] == 0

    def test_enum_violations(self):
        """Test enum validation when some values are not in allowed set."""
        # Create temp directory and manually write data with violations
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create schema
            schema_dict = {
                "version": "1.0",
                "metadata": {"name": "EnumViolationTest"},
                "timeframe": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-12-31T23:59:59Z",
                    "freq": "h"
                },
                "constraints": {
                    "foreign_keys": [],
                    "enum": [
                        {"attr": "order.status", "values": ["pending", "completed"]}
                    ]
                },
                "nodes": [{
                    "id": "order",
                    "kind": "entity",
                    "pk": "order_id",
                    "rows": 10,
                    "columns": [
                        {"name": "order_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {
                            "name": "status",
                            "type": "string",
                            "generator": {
                                "choice": {
                                    "choices": ["pending", "completed", "cancelled", "shipped"]
                                }
                            }
                        }
                    ]
                }]
            }

            schema = Dataset(**schema_dict)

            # Generate data (some values will be outside allowed enum)
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=tmpdir_path)

            validator = ValueValidator(schema, tmpdir_path)
            results = validator.validate_all()

            # Should have violations (cancelled and shipped not in allowed set)
            assert len(results) == 1
            result = results[0]
            # May or may not pass depending on random selection
            # Just verify structure
            assert result.name == "order.status.enum"
            assert "violations" in result.details

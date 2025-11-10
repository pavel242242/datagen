"""Tests for validation report generation."""

import pytest
import tempfile
import json
from pathlib import Path

from datagen.core.schema import Dataset
from datagen.core.executor import DatasetExecutor
from datagen.validation.report import ValidationReport


class TestValidationReport:
    """Tests for ValidationReport class."""

    def test_report_quality_score_all_pass(self):
        """Test quality score when all validations pass."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "QualityScoreTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "ranges": [
                    {"attr": "metric.value", "min": 0, "max": 200}
                ]
            },
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "metric_id",
                "rows": 50,
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

            report = ValidationReport(schema, Path(tmpdir))
            report.run_all_validations()

            # Quality score should be high since constraints are met
            assert report.quality_score >= 90.0
            assert report.quality_score <= 100.0

    def test_report_summary_structure(self):
        """Test that report summary has correct structure."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "SummaryTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "test",
                "kind": "entity",
                "pk": "test_id",
                "rows": 30,
                "columns": [
                    {"name": "test_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            report = ValidationReport(schema, Path(tmpdir))
            report.run_all_validations()

            summary = report.get_summary()

            # Verify summary structure
            assert "total_validations" in summary
            assert "passed" in summary
            assert "failed" in summary
            assert "quality_score" in summary
            assert "by_table" in summary
            assert "by_type" in summary

            # Verify by_type structure
            assert "structural" in summary["by_type"]
            assert "value" in summary["by_type"]
            assert "behavioral" in summary["by_type"]

    def test_report_get_failures(self):
        """Test getting failed validations."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "FailuresTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [],
                "ranges": [
                    {"attr": "metric.value", "min": 200, "max": 300}  # Will fail
                ]
            },
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "metric_id",
                "rows": 50,
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

            report = ValidationReport(schema, Path(tmpdir))
            report.run_all_validations()

            failures = report.get_failures()

            # Should have at least one failure (range constraint)
            assert len(failures) > 0
            assert all("name" in f for f in failures)
            assert all("message" in f for f in failures)

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "ToDictTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "test",
                "kind": "entity",
                "pk": "test_id",
                "rows": 20,
                "columns": [
                    {"name": "test_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            report = ValidationReport(schema, Path(tmpdir))
            report.run_all_validations()

            report_dict = report.to_dict()

            # Verify structure
            assert "metadata" in report_dict
            assert "summary" in report_dict
            assert "failures" in report_dict
            assert "all_results" in report_dict

            # Verify metadata
            assert report_dict["metadata"]["dataset_name"] == "ToDictTest"
            assert report_dict["metadata"]["version"] == "1.0"
            assert "timestamp" in report_dict["metadata"]

    def test_report_to_json(self):
        """Test writing report to JSON file."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "JSONTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "test",
                "kind": "entity",
                "pk": "test_id",
                "rows": 15,
                "columns": [
                    {"name": "test_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            report = ValidationReport(schema, Path(tmpdir))
            report.run_all_validations()

            # Write to JSON
            json_path = Path(tmpdir) / "report.json"
            report.to_json(json_path)

            # Verify file exists
            assert json_path.exists()

            # Read and verify
            with open(json_path) as f:
                data = json.load(f)

            assert data["metadata"]["dataset_name"] == "JSONTest"
            assert "summary" in data
            assert "all_results" in data

    def test_report_print_summary(self):
        """Test human-readable summary output."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "PrintSummaryTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "test",
                "kind": "entity",
                "pk": "test_id",
                "rows": 25,
                "columns": [
                    {"name": "test_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            report = ValidationReport(schema, Path(tmpdir))
            report.run_all_validations()

            summary_text = report.print_summary()

            # Verify key elements are in the output
            assert "VALIDATION REPORT" in summary_text
            assert "Dataset: PrintSummaryTest" in summary_text
            assert "Quality Score:" in summary_text
            assert "Total Validations:" in summary_text
            assert "Passed:" in summary_text

    def test_report_empty_results(self):
        """Test report with no validation results."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "EmptyResults"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "test",
                "kind": "entity",
                "pk": "test_id",
                "rows": 10,
                "columns": [
                    {"name": "test_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            # Create report but don't run validations
            report = ValidationReport(schema, Path(tmpdir))

            # Compute quality score with no results
            report._compute_quality_score()

            # Should handle empty results gracefully
            assert report.quality_score == 0.0

    def test_report_by_table_grouping(self):
        """Test that results are grouped by table correctly."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "ByTableTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {
                "foreign_keys": [
                    {"from": "order.customer_id", "to": "customer.customer_id"}
                ],
                "ranges": [
                    {"attr": "customer.age", "min": 18, "max": 100},
                    {"attr": "order.amount", "min": 0, "max": 1000}
                ]
            },
            "nodes": [
                {
                    "id": "customer",
                    "kind": "entity",
                    "pk": "customer_id",
                    "rows": 30,
                    "columns": [
                        {"name": "customer_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {
                            "name": "age",
                            "type": "int",
                            "generator": {
                                "distribution": {
                                    "type": "uniform",
                                    "params": {"low": 20, "high": 80},
                                    "clamp": [18, 100]
                                }
                            }
                        }
                    ]
                },
                {
                    "id": "order",
                    "kind": "fact",
                    "pk": "order_id",
                    "parents": ["customer"],
                    "fanout": {"distribution": "uniform", "min": 1, "max": 3},
                    "columns": [
                        {"name": "order_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {"name": "customer_id", "type": "int", "generator": {"lookup": {"from": "customer.customer_id"}}},
                        {
                            "name": "amount",
                            "type": "float",
                            "generator": {
                                "distribution": {
                                    "type": "uniform",
                                    "params": {"low": 10, "high": 500},
                                    "clamp": [0, 1000]
                                }
                            }
                        }
                    ]
                }
            ]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            report = ValidationReport(schema, Path(tmpdir))
            report.run_all_validations()

            summary = report.get_summary()

            # Should have results for both tables
            assert "customer" in summary["by_table"]
            assert "order" in summary["by_table"]

            # Each table should have at least one validation
            assert summary["by_table"]["customer"]["total"] > 0
            assert summary["by_table"]["order"]["total"] > 0

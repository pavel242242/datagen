"""Tests for composite effect validation in behavioral validator."""

import pytest
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path

from datagen.core.schema import Dataset
from datagen.core.executor import DatasetExecutor
from datagen.validation.behavioral import BehavioralValidator


class TestCompositeEffectValidation:
    """Tests for composite effect validation (dow + hour seasonality)."""

    def test_composite_effect_dow_hour_seasonality(self):
        """Test composite effect validation with dow and hour seasonality."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "CompositeEffectTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "composite_effect": {
                    "table": "event",
                    "metric": "occurrence_rate",
                    "influences": [
                        {
                            "kind": "seasonality",
                            "dimension": "dow",
                            "weights": [1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 1.5]
                        },
                        {
                            "kind": "seasonality",
                            "dimension": "hour",
                            "weights": [0.5, 0.5, 0.5, 0.5, 0.5, 0.8, 1.0, 1.2,
                                       1.5, 1.8, 2.0, 2.0, 2.0, 2.0, 2.0, 1.8,
                                       1.5, 1.2, 1.0, 0.8, 0.8, 0.7, 0.6, 0.5]
                        }
                    ],
                    "tolerance": {
                        "mae": 0.01,
                        "mape": 20.0
                    }
                }
            },
            "nodes": [{
                "id": "event",
                "kind": "entity",
                "pk": "event_id",
                "rows": 1000,
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

            # Should have one result for composite_effect
            assert len(results) == 1
            result = results[0]
            assert result.name == "event.composite_effect"
            assert "mae" in result.details.keys()
            assert "mape" in result.details.keys()
            assert "dimensions" in result.details
            assert set(result.details["dimensions"]) == {"dow", "hour"}

    def test_composite_effect_dow_only(self):
        """Test composite effect validation with dow seasonality only."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "CompositeEffectDowOnly"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "composite_effect": {
                    "table": "event",
                    "metric": "occurrence_rate",
                    "influences": [
                        {
                            "kind": "seasonality",
                            "dimension": "dow",
                            "weights": [1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 1.5]
                        }
                    ],
                    "tolerance": {
                        "mae": 0.05,
                        "mape": 30.0
                    }
                }
            },
            "nodes": [{
                "id": "event",
                "kind": "entity",
                "pk": "event_id",
                "rows": 500,
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

            # Should have one result for composite_effect
            assert len(results) == 1
            result = results[0]
            assert result.name == "event.composite_effect"
            assert result.details["dimensions"] == ["dow"]

    def test_composite_effect_no_datetime_column(self):
        """Test composite effect validation when no datetime column exists."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "CompositeEffectNoDatetime"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "composite_effect": {
                    "table": "event",
                    "metric": "occurrence_rate",
                    "influences": [
                        {
                            "kind": "seasonality",
                            "dimension": "dow",
                            "weights": [1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 1.5]
                        }
                    ],
                    "tolerance": {
                        "mae": 0.05,
                        "mape": 30.0
                    }
                }
            },
            "nodes": [{
                "id": "event",
                "kind": "entity",
                "pk": "event_id",
                "rows": 50,
                "columns": [
                    {"name": "event_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {"name": "value", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}}
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            executor.execute(output_dir=Path(tmpdir))

            validator = BehavioralValidator(schema, Path(tmpdir))
            results = validator.validate_all()

            # Should fail with no datetime column found
            assert len(results) == 1
            result = results[0]
            assert not result.passed
            assert "datetime" in result.message.lower()

    def test_composite_effect_table_not_found(self):
        """Test composite effect validation when table doesn't exist."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "CompositeEffectMissingTable"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "composite_effect": {
                    "table": "missing_table",
                    "metric": "occurrence_rate",
                    "influences": [
                        {
                            "kind": "seasonality",
                            "dimension": "dow",
                            "weights": [1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 1.5]
                        }
                    ],
                    "tolerance": {
                        "mae": 0.05,
                        "mape": 30.0
                    }
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

    def test_composite_effect_no_recognized_dimensions(self):
        """Test composite effect validation with no recognized seasonality dimensions."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "CompositeEffectNoRecognizedDimensions"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "h"
            },
            "constraints": {"foreign_keys": []},
            "targets": {
                "composite_effect": {
                    "table": "event",
                    "metric": "occurrence_rate",
                    "influences": [
                        {
                            "kind": "outliers",
                            "mode": "drop",
                            "rate": 0.01
                        }
                    ],
                    "tolerance": {
                        "mae": 0.05,
                        "mape": 30.0
                    }
                }
            },
            "nodes": [{
                "id": "event",
                "kind": "entity",
                "pk": "event_id",
                "rows": 50,
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
                                "freq": "h"
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

            # Should fail with no recognized dimensions
            assert len(results) == 1
            result = results[0]
            assert not result.passed
            assert "no recognized" in result.message.lower() or "dimensions" in result.message.lower()

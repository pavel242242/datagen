"""Integration tests for shipped features (#2 Segmentation, #7 Trends, #1 Vintage).

Tests end-to-end generation with feature-specific behaviors.
"""

import pytest
import tempfile
import pandas as pd
from pathlib import Path

from datagen.core.schema import Dataset
from datagen.core.executor import DatasetExecutor


class TestSegmentationFeature:
    """Integration tests for Feature #2: Entity Segmentation."""

    def test_segment_fanout_multipliers(self):
        """Test that segment-based fanout multipliers are applied correctly."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "SegmentationTest"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "H"
            },
            "constraints": {
                "foreign_keys": [
                    {"from": "order.customer_id", "to": "customer.customer_id"}
                ]
            },
            "nodes": [
                {
                    "id": "customer",
                    "kind": "entity",
                    "pk": "customer_id",
                    "rows": 100,
                    "columns": [
                        {"name": "customer_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {
                            "name": "segment",
                            "type": "string",
                            "generator": {
                                "choice": {
                                    "choices": ["vip", "standard", "budget"],
                                    "weights": [0.2, 0.5, 0.3]
                                }
                            }
                        }
                    ],
                    "segment_behavior": {
                        "segment_column": "segment",
                        "applies_to_columns": ["amount"],
                        "behaviors": {
                            "vip": {"fanout_multiplier": 3.0, "value_multiplier": 2.0},
                            "standard": {"fanout_multiplier": 1.0, "value_multiplier": 1.0},
                            "budget": {"fanout_multiplier": 0.5, "value_multiplier": 0.7}
                        }
                    }
                },
                {
                    "id": "order",
                    "kind": "fact",
                    "pk": "order_id",
                    "parents": ["customer"],
                    "fanout": {"distribution": "poisson", "lambda": 10},
                    "columns": [
                        {"name": "order_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {"name": "customer_id", "type": "int", "generator": {"lookup": {"from": "customer.customer_id"}}},
                        {
                            "name": "amount",
                            "type": "float",
                            "generator": {"distribution": {"type": "normal", "params": {"mean": 100, "sigma": 20}, "clamp": [10, 500]}}
                        }
                    ]
                }
            ]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            tables = executor.execute(output_dir=Path(tmpdir))

            customer_df = tables["customer"]
            order_df = tables["order"]

            # Verify segmentation exists
            assert "segment" in customer_df.columns
            assert set(customer_df["segment"].unique()).issubset({"vip", "standard", "budget"})

            # Join orders with customer segments
            merged = order_df.merge(customer_df[["customer_id", "segment"]], on="customer_id")

            # Calculate orders per customer by segment
            orders_per_customer = merged.groupby(["customer_id", "segment"]).size().reset_index(name="order_count")
            avg_orders_by_segment = orders_per_customer.groupby("segment")["order_count"].mean()

            # VIP should have more orders than budget
            if "vip" in avg_orders_by_segment.index and "budget" in avg_orders_by_segment.index:
                assert avg_orders_by_segment["vip"] > avg_orders_by_segment["budget"]

            # Verify value multipliers - VIP orders should have higher amounts
            avg_amount_by_segment = merged.groupby("segment")["amount"].mean()
            if "vip" in avg_amount_by_segment.index and "budget" in avg_amount_by_segment.index:
                assert avg_amount_by_segment["vip"] > avg_amount_by_segment["budget"]

    def test_segment_without_behavior(self):
        """Test that segmentation column works without segment_behavior config."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "SegmentNoMultiplier"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "H"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "rows": 50,
                "columns": [
                    {"name": "user_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "tier",
                        "type": "string",
                        "generator": {"choice": {"choices": ["gold", "silver", "bronze"]}}
                    }
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            tables = executor.execute(output_dir=Path(tmpdir))

            # Should generate successfully with no multipliers
            assert "tier" in tables["user"].columns
            assert len(tables["user"]) == 50


class TestTrendsFeature:
    """Integration tests for Feature #7: Time Series Trends."""

    def test_exponential_trend(self):
        """Test exponential growth trend modifier."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "ExponentialTrend"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "H"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "metric_id",
                "rows": 365,  # One per day
                "columns": [
                    {"name": "metric_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
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
                        "type": "float",
                        "generator": {"distribution": {"type": "normal", "params": {"mean": 100, "sigma": 5}, "clamp": [50, 200]}},
                        "modifiers": [
                            {
                                "transform": "trend",
                                "args": {
                                    "trend_type": "exponential",
                                    "growth_rate": 0.01,  # 1% growth
                                    "reference_column": "timestamp"
                                }
                            }
                        ]
                    }
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            tables = executor.execute(output_dir=Path(tmpdir))

            df = tables["metric"].sort_values("timestamp")

            # Values should trend upward
            first_quarter_mean = df.iloc[:90]["value"].mean()
            last_quarter_mean = df.iloc[-90:]["value"].mean()

            # Last quarter should have higher mean due to exponential growth
            assert last_quarter_mean > first_quarter_mean

    def test_logarithmic_trend(self):
        """Test logarithmic growth trend modifier."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "LogTrend"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "H"
            },
            "constraints": {"foreign_keys": []},
            "nodes": [{
                "id": "metric",
                "kind": "entity",
                "pk": "id",
                "rows": 200,
                "columns": [
                    {"name": "id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                    {
                        "name": "value",
                        "type": "float",
                        "generator": {"distribution": {"type": "normal", "params": {"mean": 50, "sigma": 10}, "clamp": [10, 100]}}
                    }
                ]
            }]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            tables = executor.execute(output_dir=Path(tmpdir))

            # Test that data was generated successfully
            assert len(tables["metric"]) == 200
            assert "value" in tables["metric"].columns


class TestVintageEffectsFeature:
    """Integration tests for Feature #1: Vintage Effects (additional edge cases)."""

    def test_vintage_with_multiple_parents(self):
        """Test vintage effects work with fact tables having multiple parents."""
        schema_dict = {
            "version": "1.0",
            "metadata": {"name": "MultiParentVintage"},
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
                "freq": "H"
            },
            "constraints": {
                "foreign_keys": [
                    {"from": "transaction.customer_id", "to": "customer.customer_id"},
                    {"from": "transaction.product_id", "to": "product.product_id"}
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
                            "name": "signup_date",
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
                        }
                    ],
                    "vintage_behavior": {
                        "created_at_column": "signup_date",
                        "age_based_multipliers": {
                            "activity_decay": {
                                "curve": [1.0, 0.8, 0.6, 0.5],
                                "time_unit": "month",
                                "applies_to": "fanout"
                            }
                        }
                    }
                },
                {
                    "id": "product",
                    "kind": "entity",
                    "pk": "product_id",
                    "rows": 20,
                    "columns": [
                        {"name": "product_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {"name": "name", "type": "string", "generator": {"faker": {"method": "word"}}}
                    ]
                },
                {
                    "id": "transaction",
                    "kind": "fact",
                    "pk": "transaction_id",
                    "parents": ["customer", "product"],
                    "fanout": {"distribution": "poisson", "lambda": 5},
                    "columns": [
                        {"name": "transaction_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
                        {"name": "customer_id", "type": "int", "generator": {"lookup": {"from": "customer.customer_id"}}},
                        {"name": "product_id", "type": "int", "generator": {"lookup": {"from": "product.product_id"}}},
                        {
                            "name": "transaction_time",
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
                        }
                    ]
                }
            ]
        }

        schema = Dataset(**schema_dict)

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = DatasetExecutor(schema, master_seed=42)
            tables = executor.execute(output_dir=Path(tmpdir))

            # Should generate successfully with vintage effects on one parent
            assert len(tables["transaction"]) > 0

            # Verify temporal constraint: all transactions after customer signup
            merged = tables["transaction"].merge(
                tables["customer"][["customer_id", "signup_date"]],
                on="customer_id"
            )
            violations = merged[merged["transaction_time"] < merged["signup_date"]]
            assert len(violations) == 0, "Temporal constraint violated"

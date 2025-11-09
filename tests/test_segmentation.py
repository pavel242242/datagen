"""Tests for entity segmentation feature."""

import pytest
import pandas as pd
import numpy as np
from src.datagen.core.schema import Dataset
from src.datagen.core.executor import DatasetExecutor


def test_segmentation_fanout_multipliers(tmp_path):
    """Test that segment_behavior affects fanout for different segments."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "SegmentationTest"},
        "timeframe": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z",
            "freq": "H"
        },
        "constraints": {},
        "nodes": [
            {
                "id": "customer",
                "kind": "entity",
                "pk": "customer_id",
                "rows": 300,
                "columns": [
                    {
                        "name": "customer_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    },
                    {
                        "name": "segment",
                        "type": "string",
                        "nullable": False,
                        "generator": {
                            "choice": {
                                "choices": ["premium", "standard", "basic"],
                                "weights": [0.10, 0.60, 0.30]
                            }
                        }
                    }
                ],
                "segment_behavior": {
                    "segment_column": "segment",
                    "behaviors": {
                        "premium": {
                            "fanout_multiplier": 5.0,
                            "value_multiplier": 3.0
                        },
                        "standard": {
                            "fanout_multiplier": 1.0,
                            "value_multiplier": 1.0
                        },
                        "basic": {
                            "fanout_multiplier": 0.3,
                            "value_multiplier": 0.5
                        }
                    },
                    "applies_to_columns": ["amount"]
                }
            },
            {
                "id": "purchase",
                "kind": "fact",
                "pk": "purchase_id",
                "parents": ["customer"],
                "fanout": {
                    "distribution": "poisson",
                    "lambda": 10,
                    "min": 0,
                    "max": 100
                },
                "columns": [
                    {
                        "name": "purchase_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    },
                    {
                        "name": "customer_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"lookup": {"from": "customer.customer_id"}}
                    },
                    {
                        "name": "amount",
                        "type": "float",
                        "nullable": False,
                        "generator": {
                            "distribution": {
                                "type": "normal",
                                "params": {"mu": 100, "sigma": 20},
                                "clamp": [10, 500]
                            }
                        }
                    }
                ]
            }
        ]
    }

    # Generate dataset
    output_dir = tmp_path / "output"
    dataset = Dataset(**schema)
    executor = DatasetExecutor(dataset, master_seed=42)
    executor.execute(str(output_dir))

    # Load data
    customer_df = pd.read_parquet(output_dir / "customer.parquet")
    purchase_df = pd.read_parquet(output_dir / "purchase.parquet")

    # Test segment distribution in customers
    assert len(customer_df) == 300
    assert set(customer_df['segment'].unique()) == {'premium', 'standard', 'basic'}

    # Group purchases by customer segment
    merged = purchase_df.merge(customer_df[['customer_id', 'segment']], on='customer_id')
    purchases_by_segment = merged.groupby('segment').size()

    # Premium customers (5x multiplier) should have ~5x more purchases than standard
    # Standard customers (1x multiplier) should have ~3.3x more purchases than basic (0.3x)
    premium_count = purchases_by_segment['premium']
    standard_count = purchases_by_segment['standard']
    basic_count = purchases_by_segment['basic']

    # Count customers per segment
    customers_by_segment = customer_df.groupby('segment').size()
    premium_customers = customers_by_segment['premium']
    standard_customers = customers_by_segment['standard']
    basic_customers = customers_by_segment['basic']

    # Calculate average purchases per customer
    avg_premium = premium_count / premium_customers
    avg_standard = standard_count / standard_customers
    avg_basic = basic_count / basic_customers

    # Premium should have ~5x standard's average
    premium_vs_standard_ratio = avg_premium / avg_standard
    assert 4.0 < premium_vs_standard_ratio < 6.0, f"Premium/Standard ratio {premium_vs_standard_ratio:.2f} not near 5.0"

    # Standard should have ~3.3x basic's average (1.0 / 0.3)
    standard_vs_basic_ratio = avg_standard / avg_basic
    assert 2.5 < standard_vs_basic_ratio < 4.5, f"Standard/Basic ratio {standard_vs_basic_ratio:.2f} not near 3.3"


def test_segmentation_value_multipliers(tmp_path):
    """Test that segment_behavior affects column values for different segments."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "ValueMultiplierTest"},
        "timeframe": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z",
            "freq": "H"
        },
        "constraints": {},
        "nodes": [
            {
                "id": "customer",
                "kind": "entity",
                "pk": "customer_id",
                "rows": 100,
                "columns": [
                    {
                        "name": "customer_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    },
                    {
                        "name": "tier",
                        "type": "string",
                        "nullable": False,
                        "generator": {
                            "choice": {
                                "choices": ["enterprise", "smb"],
                                "weights": [0.20, 0.80]
                            }
                        }
                    }
                ],
                "segment_behavior": {
                    "segment_column": "tier",
                    "behaviors": {
                        "enterprise": {
                            "fanout_multiplier": 1.0,
                            "value_multiplier": 10.0
                        },
                        "smb": {
                            "fanout_multiplier": 1.0,
                            "value_multiplier": 1.0
                        }
                    },
                    "applies_to_columns": ["deal_size"]
                }
            },
            {
                "id": "deal",
                "kind": "fact",
                "pk": "deal_id",
                "parents": ["customer"],
                "fanout": {
                    "distribution": "poisson",
                    "lambda": 5,
                    "min": 1,
                    "max": 20
                },
                "columns": [
                    {
                        "name": "deal_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    },
                    {
                        "name": "customer_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"lookup": {"from": "customer.customer_id"}}
                    },
                    {
                        "name": "deal_size",
                        "type": "float",
                        "nullable": False,
                        "generator": {
                            "distribution": {
                                "type": "normal",
                                "params": {"mu": 1000, "sigma": 200},
                                "clamp": [500, 2000]
                            }
                        }
                    }
                ]
            }
        ]
    }

    # Generate dataset
    output_dir = tmp_path / "output"
    dataset = Dataset(**schema)
    executor = DatasetExecutor(dataset, master_seed=42)
    executor.execute(str(output_dir))

    # Load data
    customer_df = pd.read_parquet(output_dir / "customer.parquet")
    deal_df = pd.read_parquet(output_dir / "deal.parquet")

    # Merge to get tier for each deal
    merged = deal_df.merge(customer_df[['customer_id', 'tier']], on='customer_id')

    # Calculate mean deal size by tier
    mean_by_tier = merged.groupby('tier')['deal_size'].mean()

    enterprise_mean = mean_by_tier['enterprise']
    smb_mean = mean_by_tier['smb']

    # Enterprise deals should be ~10x larger than SMB deals
    ratio = enterprise_mean / smb_mean
    assert 8.0 < ratio < 12.0, f"Enterprise/SMB deal size ratio {ratio:.2f} not near 10.0"


def test_segmentation_without_config(tmp_path):
    """Test that customers without segment_behavior work normally."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "NoSegmentTest"},
        "timeframe": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z",
            "freq": "H"
        },
        "constraints": {},
        "nodes": [
            {
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "rows": 100,
                "columns": [
                    {
                        "name": "user_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    },
                    {
                        "name": "segment",
                        "type": "string",
                        "nullable": False,
                        "generator": {
                            "choice": {
                                "choices": ["A", "B"],
                                "weights": [0.5, 0.5]
                            }
                        }
                    }
                ]
                # No segment_behavior defined
            },
            {
                "id": "event",
                "kind": "fact",
                "pk": "event_id",
                "parents": ["user"],
                "fanout": {
                    "distribution": "poisson",
                    "lambda": 10,
                    "min": 0,
                    "max": 50
                },
                "columns": [
                    {
                        "name": "event_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    },
                    {
                        "name": "user_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"lookup": {"from": "user.user_id"}}
                    }
                ]
            }
        ]
    }

    # Generate dataset
    output_dir = tmp_path / "output"
    dataset = Dataset(**schema)
    executor = DatasetExecutor(dataset, master_seed=42)
    executor.execute(str(output_dir))

    # Load data
    user_df = pd.read_parquet(output_dir / "user.parquet")
    event_df = pd.read_parquet(output_dir / "event.parquet")

    # Both segments should have similar event counts (no multipliers)
    merged = event_df.merge(user_df[['user_id', 'segment']], on='user_id')
    events_by_segment = merged.groupby('segment').size()
    users_by_segment = user_df.groupby('segment').size()

    avg_a = events_by_segment['A'] / users_by_segment['A']
    avg_b = events_by_segment['B'] / users_by_segment['B']

    # Should be roughly equal (within 30% due to Poisson variance)
    ratio = max(avg_a, avg_b) / min(avg_a, avg_b)
    assert ratio < 1.5, f"Without segment_behavior, segments should have similar averages, got ratio {ratio:.2f}"


def test_segment_column_not_found(tmp_path, caplog):
    """Test warning when segment_column doesn't exist in parent."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "MissingSegmentColumnTest"},
        "timeframe": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z",
            "freq": "H"
        },
        "constraints": {},
        "nodes": [
            {
                "id": "customer",
                "kind": "entity",
                "pk": "customer_id",
                "rows": 50,
                "columns": [
                    {
                        "name": "customer_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    }
                ],
                "segment_behavior": {
                    "segment_column": "nonexistent_segment",
                    "behaviors": {
                        "A": {"fanout_multiplier": 2.0}
                    }
                }
            },
            {
                "id": "order",
                "kind": "fact",
                "pk": "order_id",
                "parents": ["customer"],
                "fanout": {"distribution": "poisson", "lambda": 5},
                "columns": [
                    {
                        "name": "order_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    },
                    {
                        "name": "customer_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"lookup": {"from": "customer.customer_id"}}
                    }
                ]
            }
        ]
    }

    # Generate dataset - should work with warning
    output_dir = tmp_path / "output"
    dataset = Dataset(**schema)
    executor = DatasetExecutor(dataset, master_seed=42)

    import logging
    with caplog.at_level(logging.WARNING):
        executor.execute(str(output_dir))

    # Check that warning was logged
    assert any("Segment column 'nonexistent_segment' not found" in record.message for record in caplog.records)

    # Data should still be generated
    customer_df = pd.read_parquet(output_dir / "customer.parquet")
    order_df = pd.read_parquet(output_dir / "order.parquet")
    assert len(customer_df) == 50
    assert len(order_df) > 0

"""Tests for DAG builder."""

import pytest
from datagen.core.schema import validate_schema
from datagen.core.dag import build_dag


def test_simple_entity_only():
    """Test DAG with only entities (no dependencies)."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "columns": [
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            },
            {
                "id": "product",
                "kind": "entity",
                "pk": "product_id",
                "columns": [
                    {"name": "product_id", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            }
        ],
        "constraints": {}
    }

    dataset = validate_schema(schema)
    dag = build_dag(dataset)

    # Both should be in same level (no dependencies)
    assert len(dag) == 1
    assert set(dag[0]) == {"product", "user"}


def test_parent_dependency():
    """Test DAG with explicit parent dependency."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "columns": [
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            },
            {
                "id": "order",
                "kind": "fact",
                "parents": ["user"],
                "pk": "order_id",
                "fanout": {"distribution": "poisson", "lambda": 5, "min": 0, "max": 20},
                "columns": [
                    {"name": "order_id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"lookup": {"from": "user.user_id"}}}
                ]
            }
        ],
        "constraints": {}
    }

    dataset = validate_schema(schema)
    dag = build_dag(dataset)

    # Should have 2 levels: user first, then order
    assert len(dag) == 2
    assert dag[0] == ["user"]
    assert dag[1] == ["order"]


def test_lookup_dependency():
    """Test DAG inference from lookup generator."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "country",
                "kind": "entity",
                "pk": "code",
                "columns": [
                    {"name": "code", "type": "string", "nullable": False, "generator": {"choice": {"choices": ["US", "UK"]}}}
                ]
            },
            {
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "columns": [
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {"name": "country", "type": "string", "nullable": False, "generator": {"lookup": {"from": "country.code"}}}
                ]
            }
        ],
        "constraints": {}
    }

    dataset = validate_schema(schema)
    dag = build_dag(dataset)

    # country must come before user
    assert len(dag) == 2
    assert dag[0] == ["country"]
    assert dag[1] == ["user"]


def test_choices_ref_dependency():
    """Test DAG inference from choices_ref."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "status_vocab",
                "kind": "entity",
                "pk": "id",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {"name": "status", "type": "string", "nullable": False, "generator": {"enum_list": {"values": ["active", "inactive"]}}}
                ]
            },
            {
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "columns": [
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {"name": "status", "type": "string", "nullable": False, "generator": {"choice": {"choices_ref": "status_vocab.status"}}}
                ]
            }
        ],
        "constraints": {}
    }

    dataset = validate_schema(schema)
    dag = build_dag(dataset)

    # status_vocab must come before user
    assert len(dag) == 2
    assert dag[0] == ["status_vocab"]
    assert dag[1] == ["user"]


def test_multi_level_chain():
    """Test DAG with multiple dependency levels."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "columns": [
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            },
            {
                "id": "order",
                "kind": "fact",
                "parents": ["user"],
                "pk": "order_id",
                "fanout": {"distribution": "poisson", "lambda": 5},
                "columns": [
                    {"name": "order_id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"lookup": {"from": "user.user_id"}}}
                ]
            },
            {
                "id": "payment",
                "kind": "fact",
                "parents": ["order"],
                "pk": "payment_id",
                "fanout": {"distribution": "uniform", "min": 1, "max": 1},
                "columns": [
                    {"name": "payment_id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {"name": "order_id", "type": "int", "nullable": False, "generator": {"lookup": {"from": "order.order_id"}}}
                ]
            }
        ],
        "constraints": {}
    }

    dataset = validate_schema(schema)
    dag = build_dag(dataset)

    # Should have 3 levels: user -> order -> payment
    assert len(dag) == 3
    assert dag[0] == ["user"]
    assert dag[1] == ["order"]
    assert dag[2] == ["payment"]


def test_explicit_dag_used():
    """Test that explicit DAG in schema is used."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "a",
                "kind": "entity",
                "pk": "id",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            },
            {
                "id": "b",
                "kind": "entity",
                "pk": "id",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            }
        ],
        "constraints": {},
        "dag": [["a"], ["b"]]  # Explicit ordering
    }

    dataset = validate_schema(schema)
    dag = build_dag(dataset)

    # Should use explicit DAG
    assert dag == [["a"], ["b"]]


def test_circular_dependency_error():
    """Test that circular dependencies are detected."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "a",
                "kind": "entity",
                "pk": "id",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {"name": "b_id", "type": "int", "nullable": False, "generator": {"lookup": {"from": "b.id"}}}
                ]
            },
            {
                "id": "b",
                "kind": "entity",
                "pk": "id",
                "columns": [
                    {"name": "id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {"name": "a_id", "type": "int", "nullable": False, "generator": {"lookup": {"from": "a.id"}}}
                ]
            }
        ],
        "constraints": {}
    }

    dataset = validate_schema(schema)

    with pytest.raises(ValueError, match="Circular dependencies"):
        build_dag(dataset)

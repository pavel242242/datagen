"""Integration tests for Phase 1."""

import json
from pathlib import Path
from datagen.core.schema import validate_schema
from datagen.core.dag import build_dag


def test_simple_users_events_schema():
    """Test that simple_users_events.json validates successfully."""
    schema_path = Path("examples/simple_users_events.json")
    assert schema_path.exists(), f"Example schema not found: {schema_path}"

    with open(schema_path) as f:
        schema_dict = json.load(f)

    # Should validate without errors
    dataset = validate_schema(schema_dict)

    assert dataset.version == "1.0"
    assert dataset.metadata.name == "SimpleUsersEvents"
    assert len(dataset.nodes) == 2

    # Check nodes
    user_node = next(n for n in dataset.nodes if n.id == "user")
    event_node = next(n for n in dataset.nodes if n.id == "event")

    assert user_node.kind == "entity"
    assert event_node.kind == "fact"
    assert event_node.parents == ["user"]

    # Check columns
    assert len(user_node.columns) == 4
    assert len(event_node.columns) == 4

    # Check constraints
    assert "user.user_id" in dataset.constraints.unique
    assert "event.event_id" in dataset.constraints.unique
    assert len(dataset.constraints.foreign_keys) == 1

    # Check targets
    assert dataset.targets is not None
    assert dataset.targets.weekend_share is not None


def test_simple_users_events_dag():
    """Test DAG building for simple_users_events.json."""
    schema_path = Path("examples/simple_users_events.json")

    with open(schema_path) as f:
        schema_dict = json.load(f)

    dataset = validate_schema(schema_dict)
    dag = build_dag(dataset)

    # Should have 2 levels: user first, then event
    assert len(dag) == 2
    assert dag[0] == ["user"]
    assert dag[1] == ["event"]

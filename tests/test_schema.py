"""Tests for schema validation."""

import pytest
from pydantic import ValidationError
from datagen.core.schema import validate_schema, Dataset


def test_minimal_valid_schema():
    """Test that a minimal valid schema passes validation."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z",
            "freq": "D"
        },
        "nodes": [
            {
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "columns": [
                    {
                        "name": "user_id",
                        "type": "int",
                        "nullable": False,
                        "generator": {"sequence": {"start": 1, "step": 1}}
                    }
                ]
            }
        ],
        "constraints": {
            "unique": ["user.user_id"]
        }
    }

    dataset = validate_schema(schema)
    assert dataset.version == "1.0"
    assert dataset.metadata.name == "test"
    assert len(dataset.nodes) == 1
    assert dataset.nodes[0].id == "user"


def test_invalid_version():
    """Test that invalid version is rejected."""
    schema = {
        "version": "2.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [],
        "constraints": {}
    }

    with pytest.raises(ValidationError, match="Unsupported version"):
        validate_schema(schema)


def test_missing_required_field():
    """Test that missing required fields are caught."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        # Missing timeframe
        "nodes": [],
        "constraints": {}
    }

    with pytest.raises(ValidationError):
        validate_schema(schema)


def test_unknown_field_rejected():
    """Test that unknown fields are rejected."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [],
        "constraints": {},
        "unknown_field": "should_fail"
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        validate_schema(schema)


def test_entity_cannot_have_parents():
    """Test that entity nodes cannot have parents."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "user",
                "kind": "entity",
                "pk": "user_id",
                "parents": ["other"],  # Invalid for entity
                "columns": [
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            }
        ],
        "constraints": {}
    }

    with pytest.raises(ValidationError, match="entity nodes cannot have 'parents'"):
        validate_schema(schema)


def test_pk_must_exist_in_columns():
    """Test that pk must reference an actual column."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "user",
                "kind": "entity",
                "pk": "missing_id",  # Not in columns
                "columns": [
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            }
        ],
        "constraints": {}
    }

    with pytest.raises(ValidationError, match="pk 'missing_id' not found in columns"):
        validate_schema(schema)


def test_distribution_requires_clamp():
    """Test that distribution generator requires clamp."""
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
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {
                        "name": "age",
                        "type": "int",
                        "nullable": False,
                        "generator": {
                            "distribution": {
                                "type": "normal",
                                "params": {"mean": 30, "std": 5}
                                # Missing clamp
                            }
                        }
                    }
                ]
            }
        ],
        "constraints": {}
    }

    with pytest.raises(ValidationError, match="distribution must have 'clamp'"):
        validate_schema(schema)


def test_choice_requires_choices_or_ref():
    """Test that choice requires either choices or choices_ref."""
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
                    {"name": "user_id", "type": "int", "nullable": False, "generator": {"sequence": {}}},
                    {
                        "name": "status",
                        "type": "string",
                        "nullable": False,
                        "generator": {"choice": {}}  # Missing choices/choices_ref
                    }
                ]
            }
        ],
        "constraints": {}
    }

    with pytest.raises(ValidationError, match="choice must have either 'choices' or 'choices_ref'"):
        validate_schema(schema)


def test_duplicate_node_ids():
    """Test that duplicate node ids are rejected."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "D"},
        "nodes": [
            {
                "id": "user",
                "kind": "entity",
                "pk": "id1",
                "columns": [
                    {"name": "id1", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            },
            {
                "id": "user",  # Duplicate
                "kind": "entity",
                "pk": "id2",
                "columns": [
                    {"name": "id2", "type": "int", "nullable": False, "generator": {"sequence": {}}}
                ]
            }
        ],
        "constraints": {}
    }

    with pytest.raises(ValidationError, match="Duplicate node ids"):
        validate_schema(schema)


def test_invalid_datetime():
    """Test that invalid ISO8601 datetimes are rejected."""
    schema = {
        "version": "1.0",
        "metadata": {"name": "test"},
        "timeframe": {
            "start": "not-a-date",
            "end": "2024-12-31T23:59:59Z",
            "freq": "D"
        },
        "nodes": [],
        "constraints": {}
    }

    with pytest.raises(ValidationError, match="Invalid ISO8601 datetime"):
        validate_schema(schema)

"""Prompt templates for LLM-based schema generation."""

SYSTEM_PROMPT = """You are an expert data architect specializing in creating synthetic dataset schemas.

Your task is to convert natural language descriptions into valid JSON schemas for the Datagen synthetic data generator.

**Schema Structure Rules:**
1. Always include: version (1.0), metadata (name, description), timeframe, constraints, nodes
2. Constraints must list foreign_keys: [{from: "child.col", to: "parent.col"}]
3. Nodes can be "entity" (reference tables) or "fact" (transaction tables)
4. Entity nodes have no parents; fact nodes have parents array
5. All nodes need: id, kind, pk, columns
6. Facts need fanout config (distribution: poisson/uniform, lambda or min/max)

**Generator Types (use these exactly):**
- sequence: {start, step} - Sequential integers
- choice: {choices, weights?} - Random selection
- distribution: {type: "normal"/"lognormal"/"uniform"/"poisson", params, clamp?}
- faker: {method: "name"/"email"/"company"/etc, locale?}
- lookup: {from: "table.column"} - Foreign keys
- datetime_series: {within: {start, end}, freq: "D"/"H"/etc}

**Common Modifiers:**
- multiply: {factor}
- jitter: {std, mode: "add"/"mul"} - Note: "mul" for multiplicative
- clamp: {min, max}
- seasonality: {dimension: "hour"/"dow"/"month", weights}

**Response Format:**
- Output ONLY valid JSON, no markdown, no explanations
- Use proper types: int, float, string, bool, datetime, date
- Create realistic relationships (FK lookups)
- Add nullable: true for optional fields

**Example Mini-Schema:**
{
  "version": "1.0",
  "metadata": {"name": "Simple Users", "description": "Basic user events"},
  "timeframe": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z", "freq": "H"},
  "constraints": {
    "foreign_keys": [
      {"from": "event.user_id", "to": "user.user_id"}
    ]
  },
  "nodes": [
    {
      "id": "user",
      "kind": "entity",
      "pk": "user_id",
      "rows": 500,
      "columns": [
        {"name": "user_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
        {"name": "email", "type": "string", "generator": {"faker": {"method": "email"}}},
        {"name": "created_at", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}, "freq": "D"}}}
      ]
    },
    {
      "id": "event",
      "kind": "fact",
      "pk": "event_id",
      "parents": ["user"],
      "fanout": {"distribution": "poisson", "lambda": 10},
      "columns": [
        {"name": "event_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
        {"name": "user_id", "type": "int", "generator": {"lookup": {"from": "user.user_id"}}},
        {"name": "event_type", "type": "string", "generator": {"choice": {"choices": ["click", "view", "purchase"]}}},
        {"name": "timestamp", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}, "freq": "H"}}}
      ]
    }
  ]
}"""

USER_PROMPT_TEMPLATE = """Create a synthetic dataset schema for:

{description}

Requirements:
- Use realistic table and column names
- Create appropriate relationships (parent-child via FK lookups)
- Use appropriate generators for each data type
- Set reasonable row counts (entities: 100-1000, facts scale via fanout)
- Include timestamps for temporal tables
- Add modifiers for realism (jitter, seasonality where appropriate)

Output ONLY valid JSON following the schema structure."""


REPAIR_PROMPT_TEMPLATE = """The following schema has validation errors:

{schema}

Validation errors:
{errors}

Fix these errors and return ONLY the corrected JSON schema. Common fixes:
- Ensure all required fields present (version, metadata, nodes, columns)
- Check generator types match allowed list
- Verify parent references exist
- Fix typos in field names (e.g., "colums" → "columns")
- Ensure datetime strings have proper format with Z suffix
- Add missing "from" field in lookup generators

Output ONLY valid JSON, no explanations."""


CLARIFICATION_TEMPLATE = """The description is ambiguous. Please answer these yes/no questions:

{questions}

Answer format: "Q1: yes, Q2: no, Q3: yes"

Then I'll generate the schema based on your answers."""


def get_system_prompt() -> str:
    """Get the system prompt for schema generation."""
    return SYSTEM_PROMPT


def get_user_prompt(description: str) -> str:
    """Get the user prompt for schema generation."""
    return USER_PROMPT_TEMPLATE.format(description=description)


def get_repair_prompt(schema: str, errors: str) -> str:
    """Get the repair prompt for fixing validation errors."""
    return REPAIR_PROMPT_TEMPLATE.format(schema=schema, errors=errors)


def get_clarification_prompt(questions: list[str]) -> str:
    """Get clarification prompt for ambiguous descriptions."""
    questions_str = "\n".join(f"Q{i+1}: {q}" for i, q in enumerate(questions))
    return CLARIFICATION_TEMPLATE.format(questions=questions_str)

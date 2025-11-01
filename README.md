# Datagen - Universal Synthetic Dataset Generator

Universal, schema-first synthetic data generator. Define datasets in a simple JSON DSL and generate realistic, deterministic data at scale.

## Installation

```bash
pip install -e .
```

With LLM support (optional):
```bash
pip install -e ".[llm]"
```

Development:
```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Generate from Schema
```bash
datagen generate examples/simple_users_events.json --seed 42
```

### 2. Validate Output
```bash
datagen validate examples/simple_users_events.json --data ./output
```

### 3. Create Schema from Natural Language (requires LLM)
```bash
datagen create --description "Users and their orders with timestamps" > schema.json
```

## Development Status

- [x] Phase 0: Project setup
- [ ] Phase 1: Schema layer + DAG
- [ ] Phase 2: Core generators
- [ ] Phase 3: Executor + modifiers
- [ ] Phase 4: Validation + reporting
- [ ] Phase 5: LLM integration

## Documentation

See:
- `datagen_spec.md` - Complete specification
- `IMPLEMENTATION_PLAN.md` - Development roadmap
- `LLM_SCHEMA_GENERATOR_PROMPT.md` - LLM integration guide

# Datagen Implementation Plan (MVP)

## Overview
Build the MVP in 5 phases, each deliverable and testable independently. Target: ~2-3 weeks for a single developer.

---

## Phase 0: Project Setup (Day 1)

### Deliverables
- [ ] Python project structure with pyproject.toml
- [ ] Core dependencies installed (pydantic, pandas, numpy, pyarrow, faker, networkx, click/typer)
- [ ] Basic CLI skeleton with `create`, `generate`, `validate` commands
- [ ] Simple logging setup

### File Structure
```
datagen/
├── pyproject.toml
├── README.md
├── src/
│   └── datagen/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── commands.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── schema.py
│       │   ├── dag.py
│       │   ├── seed.py
│       │   ├── executor.py
│       │   ├── output.py
│       │   └── generators/
│       │       ├── __init__.py
│       │       ├── primitives.py
│       │       ├── temporal.py
│       │       ├── semantic.py
│       │       └── registry.py
│       ├── validate/
│       │   ├── __init__.py
│       │   ├── structural.py
│       │   ├── behavioral.py
│       │   └── reporter.py
│       ├── llm/
│       │   ├── __init__.py
│       │   └── schema_generator.py
│       └── utils/
│           ├── __init__.py
│           ├── locale_mapping.py
│           └── expression_eval.py
├── tests/
│   ├── __init__.py
│   ├── test_schema.py
│   ├── test_generators.py
│   └── test_end_to_end.py
└── examples/
    ├── simple_users_events.json
    └── ecommerce.json
```

### Validation
```bash
datagen --help  # shows commands
python -m datagen.cli.commands --version
```

---

## Phase 1: Schema Layer + DAG (Days 2-3)

### Deliverables
- [ ] Pydantic models for entire DSL (Dataset, Node, Column, GeneratorSpec, ModifierSpec, Constraints, Targets)
- [ ] JSON Schema validation with strict mode (reject unknown fields)
- [ ] DAG builder using NetworkX (infer from parents + references → topological generations)
- [ ] Seed derivation utilities (deterministic hash-based)

### Key Files
- `core/schema.py` — all Pydantic models matching spec
- `core/dag.py` — dependency inference, toposort
- `core/seed.py` — `derive_seed(master, *parts)` returning np.random.Generator

### Test Cases
```python
# Load minimal valid DSL → parse successfully
# Load DSL with unknown field → reject with clear error
# Infer DAG from parents + lookup refs → correct levels
# Derive seeds → same inputs = same outputs
```

### Validation
```bash
datagen validate examples/simple_users_events.json --dry-run
# Should parse schema, build DAG, print levels
```

---

## Phase 2: Core Generators (Days 4-6)

### Deliverables
- [ ] Implement all base generators:
  - `sequence(start, step, size)`
  - `choice(choices, weights, size, rng)` with zipf/head_tail support
  - `distribution(type, params, clamp, size, rng)` — normal, lognormal, uniform, poisson
  - `datetime_series(freq, start, end, pattern, rng)` — with hour/dow/month weights
  - `faker(method, locale)` — name, address with locale mapping
  - `lookup(from_table.column, on)` — FK/reference resolution
  - `fanout_per_parent(distribution, params, clamp, rng)`
- [ ] Function registry (id → callable mapping)
- [ ] Locale mapping utility (country → locale via pycountry/babel + fallback table)

### Key Files
- `core/generators/primitives.py` — sequence, choice, distribution, fanout
- `core/generators/temporal.py` — datetime_series, seasonality weights
- `core/generators/semantic.py` — Faker adapter with locale_from support
- `core/generators/registry.py` — `REGISTRY = {id: func}`, `get_generator(id)`
- `utils/locale_mapping.py` — `resolve_locale(country_code) → locale_str`

### Test Cases
```python
# sequence → [1,2,3,...]
# choice with zipf weights → verify distribution shape
# lognormal with clamp → all values in [min, max]
# datetime_series with dow pattern → higher counts on specified days
# faker with locale_from="US" → en_US names
# fanout poisson lambda=4 → mean≈4 per parent
```

### Validation
```bash
# Small test schema with one entity (users) using all generators
datagen generate tests/fixtures/all_generators.json --seed 42 --rows 1000
# Inspect output Parquet files
```

---

## Phase 3: Executor + Modifiers (Days 7-9)

### Deliverables
- [ ] Execution engine orchestrating DAG levels:
  - Entities: vectorized generation (generator → modifiers → clamp → cast)
  - Facts: iterate parents, sample fanout, generate FK + other columns
- [ ] Implement core modifiers:
  - `multiply`, `add`, `clamp`, `jitter` (numeric)
  - `time_jitter` (datetime)
  - `map_values` (categorical remapping)
  - `seasonality` (time-based multipliers)
  - `effect` (join external event table, apply multipliers/deltas)
  - `outliers` (inject rare spikes/drops)
  - `expression` (safe eval via numexpr/simpleeval)
- [ ] Clamp + dtype casting pipeline at end of each column generation
- [ ] Output manager: write Parquet + `.metadata.json` (schema hash, seeds, runtime stats)

### Key Files
- `core/executor.py` — `generate_dataset(schema, master_seed) → output_dir`
- `core/generators/modifiers.py` — all modifier functions
- `core/output.py` — Parquet writer, metadata JSON
- `utils/expression_eval.py` — safe arithmetic evaluator (whitelisted ops only)

### Test Cases
```python
# Entity generation → correct row count, PK uniqueness
# Fact generation → fanout matches distribution, FK integrity
# Modifier pipeline → jitter adds noise, clamp enforces bounds
# Seasonality modifier → higher values on specified hours/days
# Outliers modifier → ~rate fraction of rows are spikes
# Expression modifier → computed column = formula result
```

### Validation
```bash
datagen generate examples/simple_users_events.json --seed 42
# Output: users.parquet, events.parquet, .metadata.json
# Verify row counts, PK/FK integrity, numeric ranges
```

---

## Phase 4: Validation + Reporting (Days 10-12)

### Deliverables
- [ ] Structural validators:
  - PK uniqueness
  - FK integrity
  - Nullability checks
  - Dtype conformance
- [ ] Value validators:
  - Ranges (min/max)
  - Inequalities (e.g., start < end)
  - Pattern/regex
  - Enum membership
- [ ] Behavioral validators:
  - Seasonality deviation checks (observed vs declared weights)
  - Target checks (e.g., weekend_share, mean_in_range)
  - Composite effects validation (multiplicative model, MAE/MAPE)
- [ ] Quality score computation (0-100 scale)
- [ ] JSON report + Rich console summary
- [ ] Exit codes (0 = pass, 1 = fail)

### Key Files
- `validate/structural.py` — PK/FK/null/dtype checks
- `validate/behavioral.py` — seasonality, targets, composite effects
- `validate/reporter.py` — JSON report builder, quality score, Rich console output

### Test Cases
```python
# Valid dataset → all checks pass, score=100
# Missing FK → FK validator fails, score drops
# Out-of-range values → range validator fails
# Seasonality mismatch → behavioral validator warns, score drops
# Composite effects → verify MAE/MAPE within tolerance
```

### Validation
```bash
datagen validate examples/simple_users_events.json --data ./output
# Output: validation_report.json
# Console: color-coded summary with pass/fail counts
echo $?  # 0 if passed, 1 if failed
```

---

## Phase 5: LLM Integration (Days 13-15)

### Deliverables
- [ ] LLM prompt template for NL → simplified DSL conversion (see separate prompt document)
- [ ] Schema generator module:
  - Constrained JSON-only prompts
  - JSON Schema validation loop
  - Auto-repair on validation errors (max 3 retries)
  - Clarification questions (≤2 yes/no questions)
- [ ] `datagen create` command integration
- [ ] Dry-run sample mode (`--dry-run-sample N`)

### Key Files
- `llm/schema_generator.py` — `generate_schema_from_nl(description, api_key) → schema_dict`
- `llm/prompts.py` — system prompt + repair prompt templates

### Test Cases
```python
# Simple NL description → valid minimal DSL
# Ambiguous description → asks 1-2 clarification questions
# Invalid DSL on first try → auto-repairs and validates
# Complex description → produces entities + facts with FK + constraints
```

### Validation
```bash
datagen create --description "Users and their orders with timestamps" > schema.json
datagen generate schema.json --dry-run-sample 1000
# Should produce small sample and validate successfully
```

---

## Phase 6: Integration + Polish (Days 16-18)

### Deliverables
- [ ] End-to-end tests (NL → DSL → generate → validate)
- [ ] Example schemas for 3+ domains (users/events, ecommerce, weather/sensors)
- [ ] Performance testing (500k+ rows)
- [ ] Documentation: README with quickstart, examples, CLI reference
- [ ] Error message improvements (clear context, suggestions)
- [ ] Logging improvements (progress bars via Rich)

### Validation
```bash
# Full workflow tests
datagen create --description "..." > schema.json
datagen generate schema.json --seed 42
datagen validate schema.json --data ./output
# All pass with quality score ≥ 80

# Performance test
datagen generate examples/large_scale.json --rows 500000
# Completes in <5 minutes on laptop
```

---

## Success Criteria (MVP)

- [ ] **Integrity**: 100% PK uniqueness, FK validity on all test cases
- [ ] **Realism**: Visible seasonality patterns when configured; skewed distributions within clamps
- [ ] **Determinism**: Same seed → identical outputs (bit-for-bit)
- [ ] **Performance**: Generates 500k+ entity rows + facts in reasonable time (<10min on laptop)
- [ ] **Validation**: All structural/value/behavioral checks run; quality score accurate
- [ ] **LLM Path**: NL description → valid DSL → successful generation in ≤3 repair attempts
- [ ] **Usability**: Clear error messages; helpful CLI help text; example schemas work out-of-box

---

## Non-Goals (MVP)

Defer to v1.1+:
- HTML reports (JSON only for MVP)
- Pandera/DuckDB integrations for large-scale validation
- Polars backend option
- Advanced stats (GLM, hypothesis-style constraint solving)
- CSV/JSON/SQL output formats (Parquet only)
- Streaming/chunked generation for massive datasets (in-memory batching only)
- Web UI or API server

---

## Dependencies

### Core
```toml
[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.0"
pandas = "^2.0"
numpy = "^1.24"
pyarrow = "^12.0"
faker = "^18.0"
networkx = "^3.1"
click = "^8.1"  # or typer
jsonschema = "^4.17"
rich = "^13.0"  # progress bars + console output
```

### Optional (LLM path)
```toml
anthropic = "^0.25"  # or openai
pycountry = "^22.3"
babel = "^2.12"
simpleeval = "^0.9"  # safe expression evaluator
numexpr = "^2.8"  # vectorized expressions
```

### Dev
```toml
pytest = "^7.3"
pytest-cov = "^4.1"
black = "^23.3"
ruff = "^0.0.270"
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Faker too slow for 500k+ rows | Batch Faker calls (chunks of 10k), cache common values |
| Memory overflow on large fanout | Chunk parent iteration, stream to Parquet incrementally |
| LLM produces invalid DSL | Strict JSON Schema validation + auto-repair loop (max 3 retries) |
| Seasonality validation too strict | Use tolerance bands (±15% default), document tuning |
| Composite effects fail on sparse data | Warn on sparse strata, fall back to marginal checks |
| Complex expressions unsafe | Whitelist numexpr ops only; reject eval/exec |

---

## Deliverable Timeline Summary

| Phase | Days | Key Deliverable |
|-------|------|----------------|
| 0 | 1 | Project structure + CLI skeleton |
| 1 | 2-3 | Schema models + DAG builder |
| 2 | 4-6 | All base generators working |
| 3 | 7-9 | Executor + modifiers + output |
| 4 | 10-12 | Validation + reporting |
| 5 | 13-15 | LLM integration + create command |
| 6 | 16-18 | Integration tests + polish |

**Total: ~18 days (3-4 weeks with buffer)**

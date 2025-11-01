# CLAUDE.md - AI Assistant Context

> **Purpose**: This file provides comprehensive context for AI assistants (like Claude) working on the Datagen codebase. It explains architecture, conventions, and development practices.

---

## Project Overview

**Datagen** is a universal, schema-first synthetic dataset generator that creates realistic, deterministic tabular data from declarative JSON schemas.

**Core Value Proposition:**
- Schema-driven (JSON DSL) - no code generation, safer for LLM usage
- Deterministic (same seed → same output)
- Relational (multi-table with FK integrity)
- Validated (comprehensive quality scoring)
- Fast (vectorized numpy/pandas)

**Status:** MVP complete (57/57 tests passing), LLM integration planned

---

## Architecture

### High-Level Data Flow

```
JSON Schema → Schema Validation (Pydantic) → DAG Builder (NetworkX)
                                                    ↓
                                            Generation Levels
                                                    ↓
                    ┌───────────────────────────────┴──────────────────────────────┐
                    ↓                                                              ↓
            Entity Generation                                              Fact Generation
        (vectorized, 1000 rows)                              (batched, parent-driven fanout)
                    ↓                                                              ↓
            └───────────────────────────────────┬──────────────────────────────────┘
                                                ↓
                                        Output Manager
                                    (Parquet + metadata.json)
                                                ↓
                                          Validator
                            (structural + value + behavioral checks)
                                                ↓
                                    Quality Report (JSON)
```

### Core Components

#### 1. Schema Layer (`src/datagen/core/schema.py`)

**Purpose:** Pydantic models defining the JSON DSL structure

**Key Classes:**
- `Dataset` - Top-level schema container
- `Node` - Entity or fact table definition
- `Column` - Column specification with generator/modifiers
- `GeneratorSpec` - Union of all generator types
- `ModifierSpec` - Union of all modifier types
- `Constraints` - Validation constraints (PK, FK, ranges, etc.)
- `Target` - Behavioral validation targets

**Important Details:**
- Uses Pydantic v2 with strict validation
- Extra fields are forbidden (`extra="forbid"`)
- Extensive use of discriminated unions (`Field(discriminator="...")`)
- Default values injected where sensible (e.g., `nullable=False`)

**When to Edit:**
- Adding new generator types
- Adding new modifier types
- Extending validation constraints
- Changing DSL structure

**Example:**
```python
class Column(BaseModel):
    name: str
    type: Literal["int", "float", "string", "date", "datetime", "bool"]
    nullable: bool = False
    generator: GeneratorSpec
    modifiers: List[ModifierSpec] = Field(default_factory=list)
```

#### 2. DAG Builder (`src/datagen/core/dag.py`)

**Purpose:** Infer table dependencies and compute generation order

**Key Function:** `build_dag(schema: Dataset) -> Tuple[nx.DiGraph, List[List[str]]]`

**Algorithm:**
1. Scan `parents` field in each node
2. Scan `lookup` generators for cross-table references
3. Build directed graph with NetworkX
4. Compute topological generations (levels)
5. Return graph + ordered levels

**Important Details:**
- Entities have no parents → appear in level 0
- Facts depend on entities → appear in level 1+
- Self-referential tables (e.g., employee.manager_id → employee.employee_id) are handled by making some FK values nullable during generation
- Cycles are rejected with clear error messages

**When to Edit:**
- Adding new generator types that create dependencies
- Improving cycle detection messages
- Optimizing level computation

**Example Output:**
```python
levels = [
    ["branch"],                    # Level 0: entities
    ["employee", "customer"],      # Level 1: depend on branch
    ["account", "transaction"]     # Level 2: depend on customer
]
```

#### 3. Seed Manager (`src/datagen/core/seed.py`)

**Purpose:** Deterministic seed derivation for reproducibility

**Key Function:** `derive_seed(master_seed: int, *parts: str) -> np.random.Generator`

**Algorithm:**
1. Concatenate master seed + parts (table name, column name, parent ID, etc.)
2. Hash with SHA256
3. Take first 8 bytes as integer seed
4. Return `np.random.Generator(np.random.PCG64(seed))`

**Important Details:**
- Same inputs ALWAYS produce same Generator
- Different parts (table, column) produce uncorrelated seeds
- Uses modern PCG64 algorithm (better than MT19937)
- Critical for deterministic generation

**When to Edit:**
- Changing hash algorithm (requires migration plan)
- Adding seed scopes (e.g., per-row seeds)

**Example:**
```python
# Different seeds for different contexts
user_seed = derive_seed(42, "user")
age_seed = derive_seed(42, "user", "age")
email_seed = derive_seed(42, "user", "email")
```

#### 4. Generator Registry (`src/datagen/core/generators/registry.py`)

**Purpose:** Pluggable function registry for all generators

**Key Structure:**
```python
REGISTRY = {
    "sequence": generate_sequence,
    "choice": generate_choice,
    "distribution": generate_distribution,
    "datetime_series": generate_datetime_series,
    "faker": generate_faker,
    "lookup": generate_lookup,
    "expression": generate_expression,
}
```

**Generator Function Signature:**
```python
def generate_X(
    spec: XSpec,           # Pydantic spec from schema
    n_rows: int,           # Number of values to generate
    rng: np.random.Generator,  # Seeded RNG
    context: GenerationContext  # Access to parent tables, timeframe, etc.
) -> np.ndarray | pd.Series:
    ...
```

**Important Details:**
- All generators must be vectorized (generate all rows at once)
- Return numpy array or pandas Series
- Use provided RNG for all randomness (never `random.random()`)
- Access parent data via `context.tables[table_name]`

**Generator Implementations:**

**`primitives.py`:**
- `sequence(start, step)` - Sequential integers
- `choice(choices, weights_kind, weights)` - Random selection with uniform/weighted/Zipf/head-tail
- `distribution(kind, params, clamp)` - Normal, lognormal, uniform, Poisson
- Fanout logic for fact table generation

**`semantic.py`:**
- `faker(method, locale, locale_from)` - Realistic fake data
- Locale resolution: country code → locale string (US → en_US)
- Batched calls for performance

**`temporal.py`:**
- `datetime_series(within, freq, pattern)` - Time series generation
- Seasonality patterns (hour, dow, month weights)
- Uses pandas `date_range` + random sampling

**When to Edit:**
- Adding new generator types
- Optimizing slow generators
- Fixing distribution bugs

**Example Custom Generator:**
```python
def generate_uuid(spec, n_rows, rng, context):
    """Generate UUIDs deterministically from RNG."""
    import uuid
    return np.array([
        str(uuid.UUID(int=rng.integers(0, 2**128)))
        for _ in range(n_rows)
    ])

REGISTRY["uuid"] = generate_uuid
```

#### 5. Modifiers (`src/datagen/core/modifiers.py`)

**Purpose:** Transform generated values for realism

**Key Function:** `apply_modifiers(values, modifiers, context) -> values`

**Modifier Pipeline:**
Values pass through modifiers sequentially:
```
Generated Values → Modifier 1 → Modifier 2 → ... → Clamp → Cast → Final Values
```

**Available Modifiers:**
- `multiply(factor)` - Multiply by constant
- `add(delta)` - Add constant
- `clamp(min, max)` - Enforce bounds
- `jitter(scale, distribution)` - Add noise
- `time_jitter(scale, unit)` - Add time noise
- `seasonality(dimension, weights)` - Time-based multipliers
- `outliers(mode, rate, magnitude_dist)` - Inject spikes/drops
- `expression(formula)` - Arithmetic via pandas eval
- `map_values(mapping)` - Categorical remapping

**Important Details:**
- Modifiers operate on pandas Series (not numpy arrays)
- Access to `context.tables` for cross-table joins
- `seasonality` requires datetime index or column
- `expression` uses whitelisted pandas eval (safe)

**When to Edit:**
- Adding new modifier types
- Fixing modifier bugs
- Optimizing performance

**Example Modifier Chain:**
```python
# Generate base amount
amount = generate_distribution(spec, n_rows, rng, context)

# Apply modifiers
modifiers = [
    {"transform": "multiply", "args": {"factor": 1.5}},
    {"transform": "jitter", "args": {"scale": 0.1}},
    {"transform": "clamp", "args": {"min": 0, "max": 1000}}
]
amount = apply_modifiers(amount, modifiers, context)
```

#### 6. Executor (`src/datagen/core/executor.py`)

**Purpose:** Orchestrate generation across all tables

**Key Function:** `generate_dataset(schema: Dataset, master_seed: int, output_dir: str)`

**Algorithm:**
1. Build DAG and get generation levels
2. For each level:
   - For entities: generate N rows (default 1000) vectorized
   - For facts: iterate parents, sample fanout, generate child rows
3. Apply modifiers after each column generation
4. Clamp and cast to target dtype
5. Write Parquet files
6. Write metadata JSON

**Important Details:**
- Entity row count hardcoded at line 71: `n_rows = 1000`
- Fact row count determined by parent fanout (Poisson/uniform)
- FK columns use `lookup` generator with parent table reference
- Self-referential FKs allow some null values to break cycles
- Timeframe from schema used for datetime generation

**Generation Context:**
```python
class GenerationContext:
    tables: Dict[str, pd.DataFrame]  # Already-generated tables
    timeframe: Optional[Timeframe]   # Global time range
    node: Node                       # Current table being generated
```

**When to Edit:**
- Making row counts configurable
- Optimizing memory usage
- Adding streaming generation
- Improving error messages

**Example Entity Generation:**
```python
# Generate 1000 users
n_rows = 1000
df = pd.DataFrame()

for col in node.columns:
    # Derive column-specific seed
    rng = derive_seed(master_seed, node.id, col.name)

    # Generate values
    generator_func = REGISTRY[col.generator.type]
    values = generator_func(col.generator, n_rows, rng, context)

    # Apply modifiers
    values = apply_modifiers(values, col.modifiers, context)

    # Clamp and cast
    values = clamp_and_cast(values, col)

    df[col.name] = values
```

#### 7. Validator (`src/datagen/validation/`)

**Purpose:** Validate generated data against schema constraints

**Files:**
- `structural.py` - PK uniqueness, FK integrity, nullability
- `value.py` - Ranges, inequalities, patterns, enums
- `behavioral.py` - Seasonality, targets (weekend share, mean in range)
- `report.py` - Quality score computation, JSON output

**Key Function:** `validate_dataset(schema: Dataset, data_dir: str) -> Report`

**Validation Types:**

**Structural:**
```python
# Primary key uniqueness
pk_unique = df[pk_col].is_unique

# Foreign key integrity
fk_valid = child_df[fk_col].isin(parent_df[pk_col]).all()
```

**Value:**
```python
# Range constraints
in_range = df[col].between(min_val, max_val).all()

# Inequality constraints
valid = (df[start_col] < df[end_col]).all()

# Pattern matching
matches = df[col].str.match(pattern).all()
```

**Behavioral:**
```python
# Weekend share target
weekend_share = df[df['timestamp'].dt.dayofweek >= 5].shape[0] / len(df)
target_met = target_min <= weekend_share <= target_max

# Mean in range target
mean_val = df[col].mean()
target_met = target_min <= mean_val <= target_max
```

**Quality Score:**
```python
# Weighted score (0-100)
weights = {
    "structural": 0.4,  # PK/FK critical
    "value": 0.3,       # Ranges/constraints important
    "behavioral": 0.3   # Targets nice-to-have
}
score = sum(category_pass_rate * weight for category, weight in weights.items())
```

**When to Edit:**
- Adding new constraint types
- Tuning quality score weights
- Adding statistical tests
- Improving error messages

#### 8. Output Manager (`src/datagen/core/output.py`)

**Purpose:** Write generated data to disk

**Formats:**
- Parquet (default) - columnar, compressed, typed
- CSV (via export utility)
- Metadata JSON

**Parquet Settings:**
```python
df.to_parquet(
    path,
    engine="pyarrow",
    compression="snappy",  # Fast compression
    index=False
)
```

**Metadata JSON:**
```json
{
  "dataset_name": "BankSchema",
  "master_seed": 42,
  "generated_at": "2024-10-15T14:30:00Z",
  "tables": {
    "user": {"rows": 1000, "columns": 5},
    "event": {"rows": 7950, "columns": 4}
  }
}
```

**When to Edit:**
- Adding new export formats
- Changing compression settings
- Adding more metadata

---

## Development Conventions

### Code Style

**Python Version:** 3.10+

**Formatting:**
```bash
black src/ tests/ --line-length 100
ruff check src/ tests/
```

**Type Hints:**
- Use type hints for all public functions
- Use Pydantic models for structured data
- Use `Optional[T]` for nullable values

**Naming:**
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

**Example:**
```python
def generate_sequence(
    spec: SequenceSpec,
    n_rows: int,
    rng: np.random.Generator,
    context: GenerationContext
) -> np.ndarray:
    """Generate sequential integers.

    Args:
        spec: Sequence generator specification
        n_rows: Number of values to generate
        rng: Seeded random number generator
        context: Generation context with parent tables

    Returns:
        NumPy array of sequential integers
    """
    return np.arange(spec.start, spec.start + n_rows * spec.step, spec.step)
```

### Testing

**Framework:** pytest

**Test Structure:**
```
tests/
├── test_schema.py        # Pydantic model validation
├── test_dag.py           # Dependency inference
├── test_seed.py          # Deterministic seeding
├── test_generators.py    # Generator functions
├── test_phase1_*.py      # Integration tests
└── conftest.py           # Shared fixtures
```

**Writing Tests:**
```python
def test_sequence_generator():
    """Test sequence generator produces correct values."""
    spec = SequenceSpec(start=10, step=2)
    rng = derive_seed(42, "test")
    context = GenerationContext(tables={}, timeframe=None, node=None)

    result = generate_sequence(spec, n_rows=5, rng=rng, context=context)

    assert len(result) == 5
    assert list(result) == [10, 12, 14, 16, 18]
```

**Run Tests:**
```bash
# All tests
pytest tests/ -v

# Single test
pytest tests/test_generators.py::test_sequence_generator -v

# With coverage
pytest tests/ --cov=src/datagen --cov-report=html
```

**Current Status:** 57/57 tests passing

### Error Handling

**Principle:** Fail fast with clear error messages

**Schema Validation Errors:**
```python
# Pydantic automatically provides detailed validation errors
try:
    dataset = Dataset(**data)
except ValidationError as e:
    console.print(f"[red]Schema validation failed:[/red]\n{e}")
    raise SystemExit(1)
```

**Runtime Errors:**
```python
# Provide context and suggestions
if not os.path.exists(schema_path):
    raise FileNotFoundError(
        f"Schema file not found: {schema_path}\n"
        f"Try: datagen generate examples/simple_users_events.json"
    )
```

**Validation Errors:**
```python
# Don't fail, report issues in validation report
if not pk_unique:
    issues.append({
        "type": "pk_uniqueness",
        "table": table_name,
        "column": pk_col,
        "duplicates": df[df.duplicated(pk_col)][pk_col].tolist()
    })
```

### Logging

**Framework:** Python `logging` + Rich for CLI output

**Levels:**
- DEBUG: Internal state, RNG seeds, intermediate values
- INFO: Progress messages, table names, row counts
- WARNING: Non-critical issues, degraded quality
- ERROR: Validation failures, missing files

**Example:**
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Generating table: {node.id}")
logger.debug(f"Using seed: {seed}")
logger.warning(f"FK reference to non-existent table: {ref}")
```

**CLI Output:**
```python
from rich.console import Console
from rich.progress import track

console = Console()
console.print("[bold blue]Generating dataset...[/bold blue]")

for level in track(levels, description="Processing levels"):
    for table in level:
        console.print(f"  → {table}")
```

---

## Common Development Tasks

### Adding a New Generator

**Step 1:** Define Pydantic spec in `schema.py`
```python
class UUIDSpec(BaseModel):
    uuid: Literal[True] = True

GeneratorSpec = Annotated[
    Union[SequenceSpec, ChoiceSpec, ..., UUIDSpec],
    Field(discriminator="...")
]
```

**Step 2:** Implement generator in `generators/primitives.py`
```python
def generate_uuid(
    spec: UUIDSpec,
    n_rows: int,
    rng: np.random.Generator,
    context: GenerationContext
) -> np.ndarray:
    """Generate random UUIDs deterministically."""
    import uuid
    return np.array([
        str(uuid.UUID(int=rng.integers(0, 2**128)))
        for _ in range(n_rows)
    ])
```

**Step 3:** Register in `registry.py`
```python
REGISTRY["uuid"] = generate_uuid
```

**Step 4:** Add test
```python
def test_uuid_generator():
    spec = UUIDSpec()
    rng = derive_seed(42, "test")
    result = generate_uuid(spec, n_rows=10, rng=rng, context=None)

    assert len(result) == 10
    assert all(len(s) == 36 for s in result)  # UUID format
```

**Step 5:** Update documentation
- Add to `datagen_spec.md`
- Add example to README.md
- Add to test_patterns.json

### Adding a New Modifier

**Step 1:** Define Pydantic spec in `schema.py`
```python
class RoundModifier(BaseModel):
    transform: Literal["round"]
    args: dict  # {"decimals": 2}

ModifierSpec = Union[MultiplyModifier, ..., RoundModifier]
```

**Step 2:** Implement in `modifiers.py`
```python
def apply_round(values: pd.Series, args: dict) -> pd.Series:
    """Round numeric values to N decimals."""
    decimals = args.get("decimals", 0)
    return values.round(decimals)

MODIFIER_REGISTRY["round"] = apply_round
```

**Step 3:** Add to modifier pipeline in `executor.py`
```python
# Already handled by generic apply_modifiers function
```

**Step 4:** Add test
```python
def test_round_modifier():
    values = pd.Series([1.23456, 2.34567, 3.45678])
    result = apply_round(values, {"decimals": 2})

    assert list(result) == [1.23, 2.35, 3.46]
```

### Adding a New Validation Constraint

**Step 1:** Define in schema.py `Constraints` model
```python
class Constraints(BaseModel):
    pk: Optional[str] = None
    fks: List[ForeignKey] = Field(default_factory=list)
    ...
    unique: List[str] = Field(default_factory=list)  # New
```

**Step 2:** Implement validator in `validation/structural.py`
```python
def validate_unique(df: pd.DataFrame, columns: List[str]) -> Dict:
    """Validate uniqueness of column combinations."""
    issues = []
    for col in columns:
        if not df[col].is_unique:
            duplicates = df[df.duplicated(col)][col].tolist()
            issues.append({
                "column": col,
                "duplicates": duplicates
            })
    return {"passed": len(issues) == 0, "issues": issues}
```

**Step 3:** Integrate in main validation flow
```python
# In validate_dataset()
if node.constraints.unique:
    result = validate_unique(df, node.constraints.unique)
    report.add_check("unique", result)
```

**Step 4:** Add test
```python
def test_unique_constraint():
    df = pd.DataFrame({"email": ["a@b.com", "c@d.com", "a@b.com"]})
    result = validate_unique(df, ["email"])

    assert not result["passed"]
    assert len(result["issues"]) == 1
```

### Debugging Generation Issues

**Step 1:** Enable verbose logging
```bash
datagen generate schema.json --verbose
```

**Step 2:** Check intermediate values
```python
# In executor.py, add debug prints
logger.debug(f"Generated {len(values)} values")
logger.debug(f"Value range: {values.min()} - {values.max()}")
logger.debug(f"Sample values: {values[:5]}")
```

**Step 3:** Inspect output
```python
import pandas as pd
df = pd.read_parquet("output/table.parquet")
print(df.describe())
print(df.info())
```

**Step 4:** Validate output
```bash
datagen validate schema.json --data output/ -o report.json
cat report.json | jq '.issues'
```

### Performance Optimization

**Profile Generation:**
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

generate_dataset(schema, seed, output_dir)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(20)
```

**Common Bottlenecks:**
1. Faker calls → batch them
2. Large fanout → chunk parent iteration
3. Complex modifiers → vectorize operations
4. Parquet writes → use snappy compression

**Optimization Example:**
```python
# Before: slow row-by-row
names = [faker.name() for _ in range(n_rows)]

# After: batched
faker.name()  # warm up
names = [faker.name() for _ in range(n_rows)]  # still row-by-row but faster

# Better: use pandas vectorization where possible
```

---

## Schema DSL Reference (Quick Guide)

### Basic Structure

```json
{
  "version": "1.0",
  "metadata": {"name": "MyDataset"},
  "timeframe": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2025-01-01T00:00:00Z",
    "freq": "H"
  },
  "nodes": [...]
}
```

### Node Types

**Entity** (static reference table):
```json
{
  "id": "user",
  "kind": "entity",
  "pk": "user_id",
  "columns": [...]
}
```

**Fact** (temporal transaction table):
```json
{
  "id": "transaction",
  "kind": "fact",
  "pk": "transaction_id",
  "parents": ["account"],
  "fanout": {"distribution": "poisson", "lambda": 50},
  "columns": [...]
}
```

### Generator Types

**Sequence:**
```json
{"generator": {"sequence": {"start": 1, "step": 1}}}
```

**Choice:**
```json
{"generator": {"choice": {
  "choices": ["A", "B", "C"],
  "weights": [0.5, 0.3, 0.2]
}}}
```

**Distribution:**
```json
{"generator": {"distribution": {
  "kind": "normal",
  "mu": 100,
  "sigma": 15,
  "clamp": [50, 150]
}}}
```

**Faker:**
```json
{"generator": {"faker": {
  "method": "name",
  "locale": "en_US"
}}}
```

**Lookup (Foreign Key):**
```json
{"generator": {"lookup": {"from": "user.user_id"}}}
```

**Datetime Series:**
```json
{"generator": {"datetime_series": {
  "within": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2025-01-01T00:00:00Z"
  },
  "freq": "H"
}}}
```

### Modifier Types

**Multiply:**
```json
{"transform": "multiply", "args": {"factor": 1.5}}
```

**Jitter:**
```json
{"transform": "jitter", "args": {
  "scale": 0.1,
  "distribution": "normal"
}}
```

**Seasonality:**
```json
{"transform": "seasonality", "args": {
  "dimension": "dow",
  "weights": [0.8, 1.0, 1.0, 1.0, 1.0, 1.2, 1.2]
}}
```

**Outliers:**
```json
{"transform": "outliers", "args": {
  "mode": "spike",
  "rate": 0.01,
  "magnitude_dist": {"kind": "uniform", "min": 2.0, "max": 5.0}
}}
```

### Constraints

```json
"constraints": {
  "pk": "user_id",
  "fks": [
    {"column": "branch_id", "references": "branch.branch_id"}
  ],
  "ranges": [
    {"column": "age", "min": 18, "max": 80}
  ],
  "inequalities": [
    {"left": "start_date", "op": "<", "right": "end_date"}
  ],
  "enums": [
    {"column": "status", "values": ["active", "inactive"]}
  ]
}
```

---

## Troubleshooting Guide

### Common Issues

**Issue:** Import errors after editing code
```bash
# Solution: Reinstall in development mode
pip install -e . --force-reinstall
```

**Issue:** Pydantic validation errors
```python
# Check discriminator fields match exactly
# Example: generator must have one of: sequence, choice, distribution, etc.
```

**Issue:** DAG cycle detected
```python
# Check for circular dependencies in parents or lookup references
# Self-referential tables (employee.manager_id → employee.employee_id) are OK
```

**Issue:** Faker locale not found
```python
# Add mapping in src/datagen/utils/locale_mapping.py
LOCALE_MAPPING = {
    "US": "en_US",
    "DE": "de_DE",
    ...
}
```

**Issue:** Out of memory
```bash
# Reduce entity row counts in executor.py
# Or reduce fanout lambda for facts
# Or add chunking for large parent tables
```

**Issue:** Tests failing after changes
```bash
# Run specific test with verbose output
pytest tests/test_generators.py::test_sequence -vv

# Check for determinism issues (RNG seed changes)
# Check for Pydantic model changes (extra fields)
```

---

## Future Development (Roadmap)

### Phase 5: LLM Integration (Planned)

**Goal:** Natural language → JSON schema

**Approach:**
1. Constrained prompts (JSON-only output)
2. JSON Schema validation loop
3. Auto-repair on validation errors (max 3 retries)
4. Clarification questions (≤2 yes/no)

**Files to Create:**
- `src/datagen/llm/schema_generator.py`
- `src/datagen/llm/prompts.py`

**Integration:**
```bash
datagen create --description "E-commerce with users, products, orders" > schema.json
```

### v1.1 Features

- Configurable entity row counts (remove hardcode)
- Dry-run sampling mode
- HTML validation reports
- CSV/JSON export formats
- Streaming generation for massive datasets

### v2.0 Features

- Web UI for schema building
- DuckDB validation integration
- Advanced distributions (beta, gamma, etc.)
- Geographic generators (lat/lon, polygons)
- Nested JSON support

---

## Quick Reference Commands

```bash
# Generate
datagen generate schema.json --seed 42 -o ./output

# Validate
datagen validate schema.json --data ./output -o report.json

# Run tests
pytest tests/ -v

# Format code
black src/ tests/

# Check style
ruff check src/ tests/

# Profile generation
python -m cProfile -o profile.stats -m datagen.cli.commands generate schema.json
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumtime').print_stats(20)"
```

---

## Contact & Support

- **GitHub**: https://github.com/pavel242242/datagen
- **Issues**: https://github.com/pavel242242/datagen/issues
- **Documentation**: See `datagen_spec.md` for complete DSL reference

---

**For AI Assistants:** This file provides the essential context to work effectively on this codebase. When in doubt:
1. Check the existing code patterns in similar files
2. Run tests after changes (`pytest tests/ -v`)
3. Validate with example schemas (`datagen generate example/bank.json`)
4. Follow the existing code style (black, type hints, docstrings)

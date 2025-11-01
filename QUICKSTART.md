# Datagen Quickstart

## Installation

```bash
source venv/bin/activate
```

## Generate Data

### Simple Example
```bash
datagen generate examples/simple_users_events.json --seed 42 --output-dir ./output
```

This generates:
- `output/user.parquet` - 1,000 users with names, emails, ages
- `output/event.parquet` - ~8,000 events (Poisson fanout λ=8)
- `output/.metadata.json` - Generation metadata

### Complex Example (Food Delivery)
```bash
datagen generate example/valid_schema.json --seed 42 --output-dir ./output
```

This generates 13 tables with realistic food delivery data:
- Entities: customer, driver, store, product
- Facts: orders, order_items, deliveries, inventory, etc.
- With seasonality, modifiers, and relationships

## Inspect Output

### Using Python
```python
import pandas as pd

# Load data
users = pd.read_parquet('output/user.parquet')
events = pd.read_parquet('output/event.parquet')

# Inspect
print(users.head())
print(f"Users: {len(users)}, Events: {len(events)}")

# Check FK integrity
print(f"All events have valid users: {events.user_id.isin(users.user_id).all()}")
```

### Using DuckDB
```bash
duckdb -c "SELECT * FROM 'output/user.parquet' LIMIT 5"
duckdb -c "SELECT count(*) FROM 'output/event.parquet'"
```

## Check Generation Details

```bash
cat output/.metadata.json
```

Shows:
- Dataset name
- Master seed (for reproducibility)
- Row/column counts per table

## Validate Constraints (Phase 4 - Coming Soon)

```bash
datagen validate examples/simple_users_events.json --data-dir ./output
```

This will check:
- PK uniqueness
- FK integrity
- Ranges
- Inequalities
- Seasonality patterns
- Quality score

## Deterministic Generation

Same seed → same output:

```bash
# Run 1
datagen generate examples/simple_users_events.json --seed 42 -o ./run1

# Run 2
datagen generate examples/simple_users_events.json --seed 42 -o ./run2

# Compare (should be identical)
diff run1/user.parquet run2/user.parquet
```

## What Works Now (Phase 1-3)

✅ Schema validation (Pydantic + JSON Schema)
✅ DAG inference from dependencies
✅ All generators (sequence, choice, distribution, datetime, faker, lookup, expression)
✅ Entity generation (1000 rows default)
✅ Fact generation with Poisson/uniform fanout
✅ Modifiers (multiply, add, clamp, jitter, seasonality, outliers)
✅ Deterministic seeding
✅ Parquet output with metadata

## What's Coming

⏳ Phase 4: Validation engine + quality score
⏳ Phase 5: LLM integration (natural language → DSL)

## Example Schemas

- `examples/simple_users_events.json` - Basic user/event example
- `example/valid_schema.json` - Complex food delivery with all features

## Need Help?

```bash
datagen --help
datagen generate --help
datagen validate --help
```

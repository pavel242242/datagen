# How to Try Datagen Yourself

## ✅ What's Working Now (Phases 1-3)

You can generate realistic synthetic datasets with:
- Schema validation
- Multiple entities and facts with relationships
- Faker-generated names/emails
- Distributions (normal, lognormal, Poisson, uniform)
- Datetime series with seasonality patterns
- Foreign key relationships
- Deterministic seeding

## Quick Start

### 1. Activate Environment
```bash
cd /Users/chocho/projects/datagen
source venv/bin/activate
```

### 2. Generate Simple Dataset
```bash
# Generate users and events
datagen generate examples/simple_users_events.json --seed 42 --output-dir ./output

# You should see:
# ✓ Schema valid: SimpleUsersEvents
# ✅ Generation complete!
#   • user: 1,000 rows, 4 columns
#   • event: 7,950 rows, 4 columns
```

### 3. Inspect Output
```bash
# List files
ls -lh output/

# Check with Python
python -c "
import pandas as pd

users = pd.read_parquet('output/user.parquet')
events = pd.read_parquet('output/event.parquet')

print('=== USERS ===')
print(users.head())
print(f'\nTotal: {len(users)} users')

print('\n=== EVENTS ===')
print(events.head())
print(f'\nTotal: {len(events)} events')

print('\n=== FK INTEGRITY ===')
print(f'All events have valid users: {events.user_id.isin(users.user_id).all()}')

print('\n=== FANOUT STATS ===')
events_per_user = events.groupby('user_id').size()
print(f'Mean events per user: {events_per_user.mean():.2f}')
print(f'Std: {events_per_user.std():.2f}')
"
```

### 4. Check Determinism
```bash
# Same seed = same data
datagen generate examples/simple_users_events.json --seed 42 -o ./run1
datagen generate examples/simple_users_events.json --seed 42 -o ./run2

# Compare (should be identical)
python -c "
import pandas as pd
import numpy as np

u1 = pd.read_parquet('run1/user.parquet')
u2 = pd.read_parquet('run2/user.parquet')

print('Users identical:', u1.equals(u2))

e1 = pd.read_parquet('run1/event.parquet')
e2 = pd.read_parquet('run2/event.parquet')

print('Events identical:', e1.equals(e2))
"

# Clean up
rm -rf run1 run2
```

### 5. Analyze with DuckDB (Optional)
```bash
# Install duckdb if you want
# pip install duckdb

python -c "
import duckdb

# Query parquet directly
result = duckdb.sql('''
    SELECT
        u.name,
        COUNT(e.event_id) as event_count,
        AVG(e.amount) as avg_amount
    FROM 'output/user.parquet' u
    LEFT JOIN 'output/event.parquet' e ON u.user_id = e.user_id
    GROUP BY u.name
    ORDER BY event_count DESC
    LIMIT 10
''').df()

print(result)
"
```

## What You Can Customize

### Change Row Counts
Currently hardcoded to 1000 entities. To generate more/less, you'd need to modify:
```python
# In src/datagen/core/executor.py, line ~71
n_rows = 1000  # Change this
```

### Change Seeds
```bash
# Different seed = different data
datagen generate examples/simple_users_events.json --seed 123 -o ./output
```

### Modify the Schema
Edit `examples/simple_users_events.json`:
- Add more columns
- Change distributions
- Adjust fanout lambda
- Add seasonality patterns

Example - add a "premium" boolean column to users:
```json
{
  "name": "is_premium",
  "type": "bool",
  "nullable": false,
  "generator": {
    "choice": {
      "choices": [true, false],
      "weights": [0.2, 0.8]
    }
  }
}
```

## Troubleshooting

### "Module not found"
```bash
# Make sure you're in venv
source venv/bin/activate
pip list | grep datagen
```

### "File not found"
```bash
# Check you're in the right directory
pwd
# Should be: /Users/chocho/projects/datagen
```

### Output directory exists
```bash
# Clean up first
rm -rf output
```

## Next Steps (Not Yet Implemented)

### Phase 4: Validation
This will let you check data quality:
```bash
# Coming soon
datagen validate examples/simple_users_events.json --data-dir ./output
```

Will check:
- PK uniqueness ✓
- FK integrity ✓
- Value ranges ✓
- Seasonality patterns ✓
- Quality score (0-100)

### Phase 5: LLM Integration
Natural language → schema:
```bash
# Coming soon
datagen create --description "E-commerce with customers, products, orders and reviews"
```

## Example Queries to Run

### 1. Distribution of Events Per User
```python
import pandas as pd
import matplotlib.pyplot as plt

events = pd.read_parquet('output/event.parquet')
events_per_user = events.groupby('user_id').size()

print(f"Mean: {events_per_user.mean():.2f}")
print(f"Median: {events_per_user.median():.2f}")
print(f"Std: {events_per_user.std():.2f}")

# Should follow Poisson(lambda=8)
events_per_user.hist(bins=30)
plt.title('Events per User (Poisson λ=8)')
plt.savefig('fanout_dist.png')
```

### 2. Check Age Distribution
```python
import pandas as pd

users = pd.read_parquet('output/user.parquet')

print("Age stats:")
print(users['age'].describe())

# Should be normal(35, 12) clamped to [18, 80]
users['age'].hist(bins=30)
plt.title('User Age Distribution')
plt.savefig('age_dist.png')
```

### 3. Amount Distribution
```python
import pandas as pd
import numpy as np

events = pd.read_parquet('output/event.parquet')

print("Amount stats:")
print(events['amount'].describe())

# Should be lognormal(3.5, 0.8) clamped to [5, 1000]
# Will be right-skewed
plt.hist(events['amount'], bins=50)
plt.title('Event Amount (Lognormal)')
plt.savefig('amount_dist.png')
```

## Files Generated

After running generation, you'll have:
```
output/
├── user.parquet       # User table (1,000 rows)
├── event.parquet      # Event table (~8,000 rows)
└── .metadata.json     # Generation metadata
```

The `.metadata.json` contains:
```json
{
  "dataset_name": "SimpleUsersEvents",
  "version": "1.0",
  "master_seed": 42,
  "tables": {
    "user": {"rows": 1000, "columns": 4},
    "event": {"rows": 7950, "columns": 4}
  }
}
```

## Current Limitations

1. **Fixed entity row counts** - Currently 1000 rows per entity (will be configurable)
2. **No dry-run mode yet** - `--dry-run-sample N` flag exists but not implemented
3. **Complex schemas with modifiers** - Some advanced modifiers (effects, outliers) may need tweaking
4. **No validation yet** - Phase 4 will add full constraint validation

## Get Help

```bash
datagen --help
datagen generate --help
```

## Success Criteria

After generation, verify:
- ✅ Parquet files created
- ✅ Row counts match expectations (~8x fanout for events)
- ✅ FK integrity (all event.user_id in user.user_id)
- ✅ Realistic data (names are real names, emails have @)
- ✅ Distributions look right (age normal, amount lognormal)
- ✅ Deterministic (same seed → identical output)

**You're ready to generate your own datasets!** 🎉

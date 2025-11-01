# Datagen

> **Universal, schema-first synthetic dataset generator**
> Define complex, multi-table datasets in JSON and generate realistic, deterministic data at scale.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## Why Datagen?

**Generate realistic synthetic data for:**
- Development & testing
- Demos & prototypes
- Data science experiments
- Performance testing
- Privacy-compliant data sharing

**Key advantages:**
- **Schema-first**: Define everything in declarative JSON DSL—no code required
- **Deterministic**: Same seed always produces identical data
- **Realistic**: Built-in distributions, seasonality, Faker integration
- **Relational**: Multi-table datasets with proper foreign key integrity
- **Validated**: Comprehensive validation with quality scoring
- **Fast**: Vectorized generation using numpy/pandas

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/pavel242242/datagen.git
cd datagen

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Optional: Install LLM support
pip install -e ".[llm]"

# Optional: Install Keboola integration
pip install -e ".[keboola]"

# Development dependencies
pip install -e ".[dev]"
```

### Generate Your First Dataset

```bash
# Generate a simple user/events dataset
datagen generate examples/simple_users_events.json --seed 42

# Output:
# → output/user.parquet (1,000 users)
# → output/event.parquet (~8,000 events with foreign keys)
# → output/.metadata.json (generation metadata)
```

### Validate the Output

```bash
datagen validate examples/simple_users_events.json --data ./output

# Validates:
# ✓ Primary key uniqueness
# ✓ Foreign key integrity
# ✓ Value ranges and constraints
# ✓ Data distributions
# Quality Score: 100/100
```

### Inspect the Data

```python
import pandas as pd

# Load generated data
users = pd.read_parquet('output/user.parquet')
events = pd.read_parquet('output/event.parquet')

print(f"Generated {len(users)} users and {len(events)} events")
print(f"FK integrity: {events.user_id.isin(users.user_id).all()}")
print(users.head())
```

---

## Features

### 🎯 Schema-Driven Generation

Define datasets using a simple JSON DSL:

```json
{
  "version": "1.0",
  "metadata": { "name": "UserEvents" },
  "nodes": [
    {
      "id": "user",
      "kind": "entity",
      "pk": "user_id",
      "columns": [
        { "name": "user_id", "type": "int", "generator": { "sequence": { "start": 1 } } },
        { "name": "name", "type": "string", "generator": { "faker": { "method": "name" } } },
        { "name": "email", "type": "string", "generator": { "faker": { "method": "email" } } },
        { "name": "age", "type": "int", "generator": { "distribution": { "kind": "normal", "mu": 35, "sigma": 12, "clamp": [18, 80] } } }
      ]
    },
    {
      "id": "event",
      "kind": "fact",
      "pk": "event_id",
      "parents": ["user"],
      "fanout": { "distribution": "poisson", "lambda": 8 },
      "columns": [
        { "name": "event_id", "type": "int", "generator": { "sequence": { "start": 1 } } },
        { "name": "user_id", "type": "int", "generator": { "lookup": { "from": "user.user_id" } } },
        { "name": "timestamp", "type": "datetime", "generator": { "datetime_series": {} } }
      ]
    }
  ]
}
```

### 🔧 Powerful Generators

**Primitives:**
- `sequence` - Sequential integers
- `choice` - Random selection with weights, Zipf, or head-tail distributions
- `distribution` - Normal, lognormal, uniform, Poisson with automatic clamping

**Semantic:**
- `faker` - Realistic names, emails, addresses, phone numbers with locale support
- `lookup` - Foreign key references with join-based lookups

**Temporal:**
- `datetime_series` - Time series with configurable frequency and patterns
- Seasonality patterns (hour, day-of-week, month)

**Advanced:**
- `expression` - Safe arithmetic expressions using pandas eval
- `fanout` - Poisson or uniform distribution for parent-child relationships

### 🎨 Modifiers & Realism

Transform generated data for realism:

```json
{
  "modifiers": [
    { "transform": "multiply", "args": { "factor": 1.5 } },
    { "transform": "jitter", "args": { "scale": 0.1 } },
    { "transform": "seasonality", "args": {
      "dimension": "dow",
      "weights": [0.8, 1.0, 1.0, 1.0, 1.0, 1.2, 1.2]
    }},
    { "transform": "outliers", "args": {
      "mode": "spike",
      "rate": 0.01,
      "magnitude_dist": { "kind": "uniform", "min": 2.0, "max": 5.0 }
    }}
  ]
}
```

**Available modifiers:**
- `multiply`, `add` - Numeric transformations
- `clamp` - Enforce min/max bounds
- `jitter`, `time_jitter` - Add realistic noise
- `seasonality` - Time-based patterns (hour/day/month)
- `outliers` - Inject spikes or drops
- `expression` - Complex derived values

### ✅ Comprehensive Validation

Validate generated data against schema constraints:

```bash
datagen validate example/bank.json --data output_bank/ -o report.json
```

**Validates:**
- **Structural**: PK uniqueness, FK integrity, nullability
- **Value**: Ranges, inequalities, patterns, enums
- **Behavioral**: Seasonality patterns, statistical targets
- **Quality Score**: 0-100 weighted score

**Example output:**
```
✓ Primary Keys: 10/10 unique (100%)
✓ Foreign Keys: 15/15 valid (100%)
✓ Ranges: 6/6 passed
✓ Inequalities: 2/2 passed
✓ Behavioral: 8/10 targets met

Quality Score: 95.4/100
```

### 🔄 Deterministic & Reproducible

Same seed always produces identical data:

```bash
# Generate with seed 42
datagen generate schema.json --seed 42 -o run1

# Generate again with same seed
datagen generate schema.json --seed 42 -o run2

# Data is identical
diff run1/user.parquet run2/user.parquet  # No differences
```

### 📊 Real-World Examples

The repository includes battle-tested schemas:

**`example/bank.json`** - Banking system (11 tables, 147K+ rows)
- Branches, employees, customers, accounts
- Transactions, loans, cards with fraud patterns
- Self-referential (employee.manager_id → employee.employee_id)
- Quality score: 95.4/100

**`example/ecomm.json`** - E-commerce platform
- Users, products, orders, reviews
- Inventory, wishlists, categories
- Seasonality and behavioral patterns

**`example/gov_scaled.json`** - Government services
- Citizens, agencies, services, applications
- Multi-level hierarchies and dependencies

**`example/test_patterns.json`** - Comprehensive test suite
- All generators and modifiers
- Edge cases and validation scenarios

---

## Documentation

### Core Concepts

**Entities vs Facts:**
- **Entities**: Static reference tables (users, products, branches)
- **Facts**: Event/transaction tables with timestamps (orders, transactions)

**Primary & Foreign Keys:**
- Automatic FK integrity using `lookup` generator
- Support for self-referential tables
- Multi-parent relationships

**Deterministic Seeding:**
- Master seed → derived seeds for each table/column
- Hash-based derivation using SHA256
- Perfect reproducibility

### Schema DSL Reference

See [`datagen_spec.md`](./datagen_spec.md) for the complete specification.

**Key sections:**
- Node types (entity, fact)
- Column generators
- Modifier pipeline
- Constraints and validation targets
- Timeframe configuration

### CLI Reference

```bash
# Generate dataset
datagen generate <schema.json> [OPTIONS]
  --seed INT          Master seed for reproducibility (default: 42)
  --output-dir PATH   Output directory (default: ./output)
  --dry-run-sample N  Generate only N sample rows

# Validate dataset
datagen validate <schema.json> [OPTIONS]
  --data PATH         Path to generated data directory
  --output PATH       JSON report output path

# Create schema from natural language (requires LLM)
datagen create [OPTIONS]
  --description TEXT  Natural language description

# Help
datagen --help
datagen generate --help
```

---

## Advanced Usage

### Custom Row Counts

Entity row counts default to 1000. To customize, edit `src/datagen/core/executor.py:71`:

```python
n_rows = 5000  # Change from default 1000
```

*Future versions will support `row_count` in schema DSL.*

### Locale-Aware Generation

Generate data for specific locales:

```json
{
  "name": "country",
  "type": "string",
  "generator": { "choice": { "choices": ["US", "DE", "FR"] } }
},
{
  "name": "address",
  "type": "string",
  "generator": {
    "faker": {
      "method": "address",
      "locale_from": "country"
    }
  }
}
```

Datagen automatically maps country codes to locales (US → en_US, DE → de_DE).

### Export Formats

**Parquet (default):**
```bash
datagen generate schema.json --output-dir ./output
# Generates .parquet files
```

**CSV:**
```bash
# Use the export utility
python -c "
from datagen.core.output import export_to_csv
export_to_csv('output/', 'output_csv/')
"
```

### Keboola Integration

Upload generated data to Keboola:

```bash
# Set credentials
export KEBOOLA_URL="https://connection.keboola.com"
export KEBOOLA_TOKEN="your-token"

# Upload
python scripts/upload_to_keboola.py output/ my-bucket
```

See [`README_KEBOOLA.md`](./README_KEBOOLA.md) for detailed instructions.

---

## Development

### Project Structure

```
datagen/
├── src/datagen/
│   ├── cli/              # CLI commands
│   ├── core/
│   │   ├── schema.py     # Pydantic models for DSL
│   │   ├── dag.py        # Dependency inference
│   │   ├── seed.py       # Deterministic seeding
│   │   ├── executor.py   # Generation orchestration
│   │   ├── generators/   # Generator implementations
│   │   └── output.py     # Parquet/CSV export
│   ├── validation/       # Validation engine
│   ├── llm/              # LLM integration (planned)
│   └── utils/            # Helper utilities
├── tests/                # Test suite (57 tests)
├── example/              # Example schemas
└── scripts/              # Utility scripts
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/datagen --cov-report=html

# Specific test
pytest tests/test_generators.py -v
```

**Current status: 57/57 tests passing ✅**

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking (optional)
mypy src/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Development guidelines:**
- Add tests for new generators/modifiers
- Update documentation for schema changes
- Follow existing code style (black, ruff)
- Keep PRs focused and atomic

---

## Architecture

### Data Flow

```
Schema JSON → Pydantic Validation → DAG Builder → Generator Registry → Executor
                                                                          ↓
User ← Validation Report ← Validator ← Output Manager ← Generated Data
```

### Components

**Schema Layer** (`core/schema.py`)
- Pydantic models for DSL v1
- JSON Schema validation with strict mode
- Default value injection

**DAG Builder** (`core/dag.py`)
- Infers dependencies from `parents` and `lookup` references
- Topological sort using NetworkX
- Returns generation levels (entities first, then facts)

**Seed Manager** (`core/seed.py`)
- Deterministic seed derivation via SHA256
- Per-table, per-column, per-parent scoping
- Returns `np.random.Generator` instances

**Generator Registry** (`core/generators/`)
- Pluggable generator functions
- Primitives, semantic, temporal implementations
- Modifier pipeline execution

**Executor** (`core/executor.py`)
- Orchestrates generation by DAG level
- Vectorized entity generation
- Batched fact generation with fanout

**Validator** (`validation/`)
- Structural, value, behavioral checks
- Quality scoring algorithm
- JSON report generation

### Key Design Decisions

**Why Parquet?**
- Efficient columnar storage
- Type preservation (dates, decimals)
- Fast analytical queries
- Industry standard for data engineering

**Why deterministic seeding?**
- Reproducibility for testing
- Debugging data issues
- Version control for generated datasets

**Why schema-first?**
- No code = safer, easier to audit
- LLM can generate schemas (humans can't safely generate code)
- Portable across languages/platforms

**Why vectorized?**
- 10-100x faster than row-by-row
- Leverages numpy/pandas optimizations
- Scales to millions of rows

---

## Performance

### Benchmarks

Tested on MacBook Pro M1 (16GB RAM):

| Schema | Tables | Rows | Time | Memory |
|--------|--------|------|------|--------|
| Simple (user/events) | 2 | 9K | 0.8s | 45MB |
| Bank | 11 | 147K | 3.2s | 180MB |
| E-commerce | 13 | 250K | 5.1s | 320MB |
| Gov Scaled | 14 | 500K | 9.8s | 650MB |

### Scaling Tips

**For large datasets (1M+ rows):**
1. Increase entity row count gradually
2. Monitor memory usage (pandas holds data in RAM)
3. Consider chunking for massive fanout scenarios
4. Use Parquet compression (Snappy default)

**Performance bottlenecks:**
- Faker calls (batch where possible)
- Large fanout (Poisson λ > 100)
- Complex modifiers with joins

---

## Roadmap

### ✅ Completed (MVP)

- [x] Schema layer with Pydantic validation
- [x] DAG inference and topological sort
- [x] All core generators (sequence, choice, distribution, faker, lookup, datetime)
- [x] Modifiers (jitter, seasonality, outliers, expression)
- [x] Deterministic seeding
- [x] Parquet output with metadata
- [x] Comprehensive validation with quality scoring
- [x] FK integrity and self-referential support
- [x] CLI with rich output

### 🚧 In Progress

- [ ] LLM integration (natural language → schema)
- [ ] Configurable row counts per entity
- [ ] CSV/JSON export formats
- [ ] HTML validation reports

### 🔮 Future (v1.1+)

- [ ] Dry-run sampling mode
- [ ] Streaming generation for massive datasets
- [ ] Polars backend option
- [ ] Web UI for schema building
- [ ] DuckDB integration for validation at scale
- [ ] Advanced statistical distributions (beta, gamma, etc.)
- [ ] Geographic data generators (lat/lon, polygons)
- [ ] Time series forecasting integration

---

## FAQ

**Q: Can I use this for production data?**
A: Datagen is for synthetic data only. Do not use for production workloads. Always validate data quality and compliance requirements.

**Q: How do I add a custom generator?**
A: Edit `src/datagen/core/generators/registry.py` and add your function to the `REGISTRY` dict. See existing generators for examples.

**Q: Why are my datetime values all the same?**
A: Entities don't use timeframe by design (they're static). Use `kind: "fact"` for temporal data with timestamps.

**Q: Can I generate graphs or nested JSON?**
A: Currently only tabular data (flat tables). Nested structures planned for v2.0.

**Q: How do I change entity row counts?**
A: Edit `src/datagen/core/executor.py:71` to change the hardcoded value. Schema-level configuration coming soon.

**Q: Is this ready for production use?**
A: Core functionality is stable (57/57 tests passing). LLM integration is experimental. Use for development, testing, and demos.

---

## Troubleshooting

**Import errors after installation:**
```bash
# Reinstall in development mode
pip install -e . --force-reinstall
```

**Out of memory errors:**
```bash
# Reduce entity row counts or fanout lambda
# Or increase system memory
```

**Faker locale not found:**
```bash
# Check locale mapping in src/datagen/utils/locale_mapping.py
# Add custom mappings if needed
```

**Validation fails with "File not found":**
```bash
# Ensure --data path matches --output-dir from generation
datagen validate schema.json --data ./output
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with:
- [Pydantic](https://pydantic.dev/) - Data validation
- [pandas](https://pandas.pydata.org/) - Data manipulation
- [NumPy](https://numpy.org/) - Numerical computing
- [Faker](https://faker.readthedocs.io/) - Fake data generation
- [NetworkX](https://networkx.org/) - Graph algorithms
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

---

## Support

- **Issues**: [GitHub Issues](https://github.com/pavel242242/datagen/issues)
- **Documentation**: See `docs/` folder and `datagen_spec.md`
- **Examples**: See `example/` folder for working schemas

---

**Made with ❤️ for data engineers, scientists, and developers who need realistic test data.**

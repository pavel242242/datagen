# 3-System Architecture: Datagen Ecosystem

## Overview

The Datagen ecosystem is split into 3 focused, composable systems:

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│  A) DATAGEN │  →   │ B) DATACRUNCHER│  →  │ C) DATAPOLISHER│
└─────────────┘      └──────────────┘      └──────────────┘
  Generate            Analyze with          Fix issues or
  synthetic data      DuckDB analysts       approve + manifest
```

---

## A) DATAGEN (✅ Complete)

**Purpose**: Generate realistic synthetic data from JSON schemas

**Input**: JSON schema (Datagen DSL)
**Output**:
- Parquet files (tables)
- `.metadata.json` (generation metadata)

**Commands**:
```bash
datagen generate schema.json --seed 42 -o output/
datagen validate schema.json --data output/
```

**Status**: Production-ready with all Phase 1-5 features

---

## B) DATACRUNCHER (🔨 New)

**Purpose**: Analyze generated data from multiple business perspectives using DuckDB

**Input**:
- Generated data directory (parquet files)
- User personas (VP of Growth, Finance VP, Data Engineer, etc.)
- Optional: Original JSON schema for reference

**Process**:
1. Load parquet files into DuckDB
2. Spawn multiple analyst agents with different personas
3. Each analyst runs SQL queries from their perspective
4. Identify issues, discrepancies, drift from expectations

**Output**:
- `crunch_report.json` - Structured findings
  - Issues by severity (critical, high, medium, low)
  - Data quality metrics
  - Discrepancies from schema expectations
  - Drift detection (temporal violations, FK integrity, etc.)
  - Recommendations

**Commands**:
```bash
# Basic analysis with default personas
datagen crunch output/ --schema schema.json

# Custom personas
datagen crunch output/ --personas "VP Growth,CFO,Data Engineer"

# Output to file
datagen crunch output/ -o crunch_report.json

# Verbose with SQL queries
datagen crunch output/ --verbose
```

**Personas**:
- **VP of Growth**: Cohort retention, activation rates, funnel conversion
- **Finance VP**: Revenue trends, pricing consistency, payment integrity
- **Data Engineer**: FK integrity, null rates, temporal ordering, duplicates
- **Customer Success VP**: Churn patterns, engagement metrics, lifecycle health
- **Marketing VP**: Attribution chains, channel effectiveness, CAC
- **Product VP**: Feature adoption, usage patterns, activation loops

**Example Output**:
```json
{
  "analysis_date": "2024-11-10T12:00:00Z",
  "dataset": "output/",
  "personas": ["VP Growth", "Data Engineer"],
  "issues": [
    {
      "severity": "critical",
      "category": "data_quality",
      "persona": "Data Engineer",
      "finding": "Temporal violations: 47% of payments before account creation",
      "sql_query": "SELECT COUNT(*) FROM payment p JOIN account a...",
      "recommendation": "Add created_at_column to vintage_behavior in schema"
    },
    {
      "severity": "high",
      "category": "business_logic",
      "persona": "VP Growth",
      "finding": "Day 7 retention only 25% (industry avg 40-60%)",
      "recommendation": "Review onboarding funnel, add engagement checkpoints"
    }
  ],
  "metrics": {
    "tables_analyzed": 6,
    "total_rows": 36708,
    "fk_integrity": 100.0,
    "null_rate": 5.2,
    "temporal_violations": 47.2
  }
}
```

---

## C) DATAPOLISHER (🔨 New)

**Purpose**: Resolve issues found by datacruncher through 3 pathways

**Input**:
- `crunch_report.json` (from datacruncher)
- Original JSON schema
- Generated data directory
- Optional: User approval/choices

**Three Resolution Paths**:

### Path 1: Improve Schema → Regenerate
**When**: Issues are schema-level (missing constraints, wrong generators)

**Process**:
1. Analyze issues that require schema changes
2. Generate improved JSON schema
3. Regenerate data with `datagen generate`
4. Re-run datacruncher to verify fixes

**Example Issues**:
- Missing `created_at_column` in vintage_behavior
- Wrong fanout distribution (too high/low)
- Missing segment_behavior for tiered pricing
- Incorrect generator types (choice vs faker)

**Output**: `schema_improved.json`

### Path 2: Build Postprocessing Script
**When**: Issues are data-level (need transformations, computed columns)

**Process**:
1. Identify data-level fixes needed
2. Generate DuckDB or Polars script
3. Apply transformations to parquet files
4. Output corrected parquet files

**Example Issues**:
- Price needs rounding to 2 decimals
- Add computed `is_active` column based on last_login
- Normalize country codes (US → USA)
- Fill missing values with defaults
- Add aggregated metrics (lifetime_value)

**Output**:
- `postprocess.sql` (DuckDB) or `postprocess.py` (Polars)
- Corrected parquet files in `output_polished/`

### Path 3: Approve Dataset → Add Manifest
**When**: No critical issues, data is production-ready

**Process**:
1. Review all findings
2. Confirm data quality acceptable
3. Generate `.manifest.yaml` with concise metadata

**Output**: `.manifest.yaml`
```yaml
dataset_name: E-commerce Platform
generated_at: 2024-11-10T12:00:00Z
generator_version: 1.0.0
quality_score: 95/100

schema:
  source: schema.json
  seed: 42
  tables:
    - name: user
      rows: 500
      columns:
        - name: user_id
          type: int64
          nullable: false
          pk: true
        - name: email
          type: string
          nullable: false
        - name: created_at
          type: timestamp[ns]
          nullable: false

    - name: order
      rows: 1754
      columns:
        - name: order_id
          type: int64
          nullable: false
          pk: true
        - name: user_id
          type: int64
          nullable: false
          fk: user.user_id

validation:
  datacruncher_version: 1.0.0
  analyzed_by:
    - VP Growth
    - Data Engineer
  findings:
    critical: 0
    high: 0
    medium: 2
    low: 3
  metrics:
    fk_integrity: 100.0%
    temporal_violations: 0.0%
    null_rate: 2.1%

approval:
  approved: true
  approved_by: datacruncher
  approved_at: 2024-11-10T12:05:00Z
  notes: "Dataset meets quality standards for production use"
```

**Commands**:
```bash
# Auto-resolve all issues (tries Path 1 first, then Path 2)
datagen polish crunch_report.json --auto

# Interactive mode (ask user which path)
datagen polish crunch_report.json --interactive

# Force specific path
datagen polish crunch_report.json --path schema  # Path 1
datagen polish crunch_report.json --path postprocess  # Path 2
datagen polish crunch_report.json --path approve  # Path 3

# Output locations
datagen polish crunch_report.json -o polished/
```

---

## End-to-End Pipeline

### Scenario 1: Issues Found → Auto-fix → Approve

```bash
# Step 1: Generate data
datagen generate schema.json --seed 42 -o output/

# Step 2: Analyze with datacruncher
datagen crunch output/ --schema schema.json -o crunch_report.json

# Step 3: Auto-polish (fixes issues, regenerates if needed)
datagen polish crunch_report.json --auto -o polished/

# Step 4: Verify fixes
datagen crunch polished/ --schema schema.json

# Step 5: Final approval
datagen polish crunch_report.json --path approve
# → Creates .manifest.yaml
```

### Scenario 2: Iterative Refinement

```bash
# Generate
datagen generate schema_v1.json -o output_v1/

# Analyze
datagen crunch output_v1/ --personas "VP Growth,CFO"

# Issues found: "Day 7 retention only 25%"
# Manual fix: Improve onboarding funnel in schema

# Regenerate with improved schema
datagen generate schema_v2.json -o output_v2/

# Re-analyze
datagen crunch output_v2/ --personas "VP Growth,CFO"

# Approve
datagen polish crunch_report.json --path approve
```

### Scenario 3: Postprocessing Only

```bash
# Generate
datagen generate schema.json -o output/

# Analyze
datagen crunch output/

# Minor data issues (rounding, formatting)
# Generate postprocessing script
datagen polish crunch_report.json --path postprocess

# Apply postprocessing
python postprocess.py  # or duckdb < postprocess.sql

# Re-analyze polished data
datagen crunch output_polished/

# Approve
datagen polish crunch_report.json --path approve
```

---

## File Structure

```
datagen/
├── src/datagen/
│   ├── core/           # A) Datagen (existing)
│   ├── llm/            # A) LLM integration (existing)
│   ├── validation/     # A) Validation (existing)
│   │
│   ├── datacruncher/   # B) New
│   │   ├── __init__.py
│   │   ├── analyzer.py         # Main analysis orchestrator
│   │   ├── personas.py         # Persona definitions & SQL patterns
│   │   ├── duckdb_queries.py   # Common DuckDB query templates
│   │   └── report.py           # crunch_report.json generator
│   │
│   └── datapolisher/   # C) New
│       ├── __init__.py
│       ├── resolver.py         # Main resolution orchestrator
│       ├── schema_improver.py  # Path 1: Schema improvement
│       ├── postprocessor.py    # Path 2: Postprocessing script gen
│       ├── approver.py         # Path 3: Manifest generation
│       └── manifest.py         # YAML manifest utilities
│
├── examples/
│   └── personas/       # Example persona definitions
│       ├── vp_growth.yaml
│       ├── finance_vp.yaml
│       └── data_engineer.yaml
│
└── tests/
    ├── test_datacruncher.py
    └── test_datapolisher.py
```

---

## Benefits of 3-System Split

### Composability
- Use datagen standalone for quick prototyping
- Run datacruncher on ANY parquet files (not just datagen output)
- Use datapolisher with external analysis tools

### Separation of Concerns
- **Datagen**: Schema → Data (generation logic)
- **Datacruncher**: Data → Insights (analysis logic)
- **Datapolisher**: Insights → Actions (resolution logic)

### Extensibility
- Add new personas without touching datagen
- Add new resolution paths without touching datacruncher
- Swap DuckDB for other analytics engines

### CI/CD Integration
```yaml
# .github/workflows/data-quality.yml
- run: datagen generate schema.json
- run: datagen crunch output/ --fail-on-critical
- run: datagen polish --auto
- run: datagen crunch output_polished/ --fail-on-high
```

---

## Next Steps

1. ✅ Create new branch: `datacruncher-datapolisher-systems`
2. 🔨 Implement **datacruncher**:
   - Core analyzer with DuckDB
   - Persona system
   - Report generation
3. 🔨 Implement **datapolisher**:
   - Three resolution paths
   - Schema improvement logic
   - Postprocessing script generation
   - Manifest YAML generation
4. 🧪 Test end-to-end pipeline
5. 📝 Update documentation

Ready to implement!

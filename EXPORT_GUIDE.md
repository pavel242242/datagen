# Datagen Export Guide - CSV & Keboola Integration

## Overview

Datagen includes an `export` command to convert generated Parquet files to CSV format with Keboola-compatible metadata files. This enables easy integration with Keboola Connection and other data platforms.

---

## Quick Start

### 1. Generate Data

First, generate your synthetic data:

```bash
datagen generate example/bank.json -o output_bank --seed 42
```

### 2. Export to CSV

Export the generated data to CSV with metadata:

```bash
datagen export example/bank.json --data-dir output_bank -o output_bank_csv
```

---

## Command Reference

### `datagen export`

Export generated data to CSV with Keboola-compatible metadata.

**Syntax:**
```bash
datagen export <schema_path> --data-dir <input_dir> -o <output_dir> [--format <format>]
```

**Arguments:**
- `schema_path` - Path to the schema JSON file (same one used for generation)

**Options:**
- `--data-dir` - Directory containing generated Parquet files (required)
- `-o, --output-dir` - Output directory for CSV + metadata files (required)
- `--format` - Output format: `csv` (default) or `parquet`

**Examples:**

```bash
# Export to CSV with manifest files
datagen export example/bank.json --data-dir output_bank -o output_bank_csv

# Copy Parquet files (no conversion)
datagen export example/bank.json --data-dir output_bank -o output_bank_copy --format parquet
```

---

## Output Structure

### CSV Format (Default)

When exporting to CSV, the output directory contains:

```
output_bank_csv/
├── dataset.json                    # Enhanced metadata for entire dataset
├── branch.csv                      # Table data in CSV format
├── branch.csv.manifest             # Keboola manifest (table metadata)
├── customer.csv
├── customer.csv.manifest
├── account.csv
├── account.csv.manifest
└── ... (one CSV + manifest per table)
```

### File Types

#### 1. **CSV Files** (`*.csv`)

Standard CSV format with:
- UTF-8 encoding
- Comma delimiter
- Double-quote enclosure
- Header row with column names
- No index column

**Example** (`customer.csv`):
```csv
customer_id,segment,registered_at
5000,Standard,2024-11-23
5001,Standard,2024-06-26
5002,Premium,2024-07-25
```

#### 2. **Manifest Files** (`*.csv.manifest`)

Keboola-compatible manifest files with table metadata:

**Example** (`customer.csv.manifest`):
```json
{
  "name": "customer",
  "columns": [
    {
      "name": "customer_id",
      "data_type": "int64"
    },
    {
      "name": "segment",
      "data_type": "object"
    },
    {
      "name": "registered_at",
      "data_type": "datetime64[ns]"
    }
  ],
  "primary_key": [
    "customer_id"
  ],
  "delimiter": ",",
  "enclosure": "\""
}
```

**Manifest Fields:**
- `name` - Table name
- `columns` - Array of column definitions with name and data type
- `primary_key` - Array of primary key column names
- `delimiter` - CSV delimiter character (`,`)
- `enclosure` - CSV quote character (`"`)

#### 3. **Dataset Metadata** (`dataset.json`)

Enhanced metadata for the entire dataset:

**Example:**
```json
{
  "dataset_name": "BankSchema",
  "version": "1.0",
  "master_seed": 42,
  "schema_file": "example/bank.json",
  "tables": {
    "customer": {
      "rows": 1000,
      "columns": 9,
      "primary_key": "customer_id",
      "kind": "entity",
      "column_names": [
        "customer_id",
        "branch_id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "date_of_birth",
        "segment",
        "registration_date"
      ]
    },
    "account": {
      "rows": 1000,
      "columns": 7,
      "primary_key": "account_id",
      "kind": "entity",
      "column_names": [...]
    }
  },
  "generation_stats": {
    "exported_format": "csv",
    "total_tables": 10,
    "total_rows": 143098
  }
}
```

**Dataset Metadata Fields:**
- `dataset_name` - Name from schema metadata
- `version` - Schema version (DSL v1)
- `master_seed` - Seed used for generation
- `schema_file` - Path to original schema
- `tables` - Dictionary of table metadata:
  - `rows` - Number of rows in table
  - `columns` - Number of columns
  - `primary_key` - Primary key column name
  - `kind` - Table kind (entity/fact/vocab)
  - `column_names` - List of all column names
- `generation_stats` - Export statistics:
  - `exported_format` - Output format (csv/parquet)
  - `total_tables` - Number of tables exported
  - `total_rows` - Total rows across all tables

---

## Keboola Integration

### Uploading to Keboola Connection

The exported CSV files with manifest files are fully compatible with Keboola Connection. You can upload them using:

#### Option 1: Keboola CLI

```bash
# Install Keboola CLI
pip install keboola-storage-api-cli

# Configure connection
export KBC_URL="https://connection.keboola.com"
export KBC_TOKEN="your-token-here"

# Upload tables
cd output_bank_csv
for table in *.csv; do
  kbc-upload-table --bucket in.c-datagen --table ${table%.csv} --file $table --manifest ${table}.manifest
done
```

#### Option 2: Keboola Storage API

```python
from keboola.client import Client

client = Client('https://connection.keboola.com', 'your-token-here')

# Create bucket
client.buckets.create(name='datagen', stage='in')

# Upload tables
import os
for table_file in os.listdir('output_bank_csv'):
    if table_file.endswith('.csv'):
        table_name = table_file[:-4]
        client.tables.create(
            name=table_name,
            bucket_id='in.c-datagen',
            file_path=f'output_bank_csv/{table_file}',
            primary_key=['id']  # From manifest
        )
```

#### Option 3: Manual Upload via UI

1. Log in to Keboola Connection
2. Go to Storage → Tables
3. Create a new bucket (e.g., `datagen`)
4. Upload CSV files one by one
5. Keboola will automatically detect the manifest files

### Manifest File Benefits

The `.csv.manifest` files provide:
- ✅ Automatic primary key detection
- ✅ Column data type hints
- ✅ Proper CSV parsing configuration
- ✅ Incremental loading support (if enabled)

---

## Use Cases

### 1. **Local Development → Keboola Production**

```bash
# Generate test data locally
datagen generate schema.json -o output_local --seed 42

# Export to CSV
datagen export schema.json --data-dir output_local -o output_csv

# Upload to Keboola (see integration section above)
```

### 2. **CI/CD Pipeline**

```bash
#!/bin/bash
# generate_and_upload.sh

# Generate fresh synthetic data
datagen generate schemas/production.json -o /tmp/output --seed $(date +%s)

# Export to CSV
datagen export schemas/production.json --data-dir /tmp/output -o /tmp/csv_export

# Upload to Keboola
kbc-upload-bucket --bucket in.c-synthetic --dir /tmp/csv_export

# Cleanup
rm -rf /tmp/output /tmp/csv_export
```

### 3. **Data Sharing**

```bash
# Generate data
datagen generate schema.json -o output --seed 42

# Export to CSV (more portable than Parquet)
datagen export schema.json --data-dir output -o shared_data

# Zip and share
zip -r shared_data.zip shared_data/
```

### 4. **Format Conversion**

```bash
# Convert existing Parquet to CSV
datagen export schema.json --data-dir output_parquet -o output_csv

# Or copy Parquet to new location with metadata
datagen export schema.json --data-dir output_parquet -o output_copy --format parquet
```

---

## Advanced Configuration

### Custom Metadata

You can extend the manifest files with custom fields by modifying `src/datagen/core/output.py`:

```python
def write_table_metadata(df, table_name, path, schema_info=None):
    metadata = {
        "name": table_name,
        "columns": [...],
        # Add custom fields
        "created_by": "datagen",
        "data_quality": "synthetic",
        "tags": ["test", "synthetic", "qa"]
    }
    # ... rest of function
```

### Incremental Loading

Enable incremental loading in Keboola by adding to manifest:

```json
{
  "name": "customer",
  "columns": [...],
  "primary_key": ["customer_id"],
  "incremental": true
}
```

### Custom Delimiters

Export with different delimiters (requires code modification):

```python
# In write_csv function
df.to_csv(path, index=False, encoding='utf-8', sep=';')  # Use semicolon

# Update manifest
schema_info = {
    "delimiter": ";",
    "enclosure": '"'
}
```

---

## Performance Considerations

### Large Datasets

For datasets > 1M rows:

1. **Memory**: CSV export loads entire table into memory
2. **Speed**: Parquet → CSV conversion is fast (~100K rows/sec)
3. **Size**: CSV files are typically 2-3x larger than Parquet

**Recommendations**:
- For very large datasets (> 10M rows), consider direct Parquet upload to Keboola if supported
- Use `--format parquet` to avoid conversion overhead
- Split large tables into chunks if memory is constrained

### Disk Space

CSV exports typically require:
- **Parquet input**: X GB
- **CSV output**: 2-3X GB
- **Total**: 3-4X GB (both formats stored)

**Example**:
- 10M rows, 10 columns → ~500 MB Parquet → ~1.5 GB CSV → ~2 GB total

---

## Troubleshooting

### Issue: "File not found"

**Cause**: Data directory doesn't contain expected Parquet files

**Solution**:
```bash
# Check what files exist
ls -la output_bank/

# Regenerate if needed
datagen generate example/bank.json -o output_bank --seed 42

# Then export
datagen export example/bank.json --data-dir output_bank -o output_csv
```

### Issue: UTF-8 encoding errors

**Cause**: Special characters in data

**Solution**: Already handled - `write_csv` uses `encoding='utf-8'`

### Issue: Manifest not recognized by Keboola

**Cause**: Incorrect manifest format or file naming

**Solution**:
- Manifest must be named `<table>.csv.manifest`
- Must contain valid JSON
- Must include `name`, `columns`, and optionally `primary_key`

### Issue: Large datetime precision loss

**Cause**: CSV doesn't preserve microsecond precision

**Solution**:
- Use Parquet format for precise datetime: `--format parquet`
- Or customize datetime format in CSV export

---

## Examples

### Example 1: Complete Workflow

```bash
# 1. Generate synthetic bank data
datagen generate example/bank.json -o output_bank --seed 42

# 2. Validate quality
datagen validate example/bank.json --data-dir output_bank

# 3. Export to CSV
datagen export example/bank.json --data-dir output_bank -o output_bank_csv

# 4. Verify output
ls -lh output_bank_csv/
cat output_bank_csv/dataset.json
head output_bank_csv/customer.csv
```

### Example 2: Export Multiple Schemas

```bash
# Generate and export all example schemas
for schema in example/*.json; do
  name=$(basename $schema .json)
  echo "Processing $name..."

  datagen generate $schema -o output_$name --seed 42
  datagen export $schema --data-dir output_$name -o csv_$name

  echo "Exported to csv_$name/"
done
```

### Example 3: Compare Formats

```bash
# Generate once
datagen generate example/bank.json -o output_bank --seed 42

# Export to both formats
datagen export example/bank.json --data-dir output_bank -o output_csv --format csv
datagen export example/bank.json --data-dir output_bank -o output_parquet --format parquet

# Compare sizes
du -sh output_csv
du -sh output_parquet
```

---

## Summary

The `datagen export` command provides:

- ✅ CSV export with proper UTF-8 encoding
- ✅ Keboola-compatible manifest files
- ✅ Enhanced dataset metadata
- ✅ Primary key information preserved
- ✅ Column data types documented
- ✅ Simple, single-command workflow

**Typical workflow:**
```bash
datagen generate schema.json -o output --seed 42
datagen export schema.json --data-dir output -o output_csv
# Upload to Keboola or share CSV files
```

For more information:
- [Keboola Documentation](https://help.keboola.com/)
- [Datagen Schema Guide](./docs/SCHEMA_GUIDE.md)
- [Datagen Implementation Status](./IMPLEMENTATION_STATUS.md)

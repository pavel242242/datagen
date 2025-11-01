# Keboola Upload Guide

Complete guide for uploading Datagen synthetic data to Keboola Connection.

---

## ⚠️ Prerequisites - READ THIS FIRST

You need **2 credentials** to upload to Keboola:

### 1. Endpoint URL
The URL where you access Keboola (your region):
- **US**: `https://connection.keboola.com`
- **EU (Central)**: `https://connection.eu-central-1.keboola.com`
- **EU (North)**: `https://connection.north-europe.azure.keboola.com`

**How to find**: Use the URL you see when you log in to Keboola

### 2. Storage API Token
Authentication token with Storage permissions

**How to get**:
1. Log in to your Keboola endpoint
2. Click **Settings** (gear icon) → **API Tokens**
3. Click **New Token**
4. Set description: "Datagen Upload"
5. Enable **Storage** → **Read** and **Write**
6. Click **Create Token**
7. **COPY THE TOKEN** (you won't see it again!)

**📖 Detailed guide**: See `KEBOOLA_CREDENTIALS.md` for step-by-step instructions with screenshots.

---

## Setup

### Set Your Credentials

```bash
# Required: Set both endpoint and token
export KEBOOLA_URL="https://connection.keboola.com"  # Your endpoint
export KEBOOLA_TOKEN="your-token-here"               # Your token
```

### Test Connection

```bash
# Verify credentials work
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  "$KEBOOLA_URL/v2/storage/tokens/verify"
```

---

## Additional Prerequisites

1. **Keboola Connection Account**
   - Sign up at your regional endpoint
   - You should have access to a project

2. **Generated Data**
   ```bash
   # Generate synthetic data
   datagen generate example/bank.json -o output_bank --seed 42

   # Export to CSV with Keboola metadata
   datagen export example/bank.json --data-dir output_bank -o output_csv
   ```

---

## Method 1: Manual Upload via Web UI (Easiest)

### Step 1: Access Keboola Storage

1. Log in to Keboola Connection
2. Click on **Storage** in the left sidebar
3. Click on **Tables** tab

### Step 2: Create a Bucket

1. Click **New Bucket**
2. Enter bucket details:
   - **Name**: `datagen` (or your preferred name)
   - **Stage**: `in` (input data)
   - **Description**: "Synthetic data from Datagen"
3. Click **Create Bucket**

### Step 3: Upload Tables

For each CSV file in your export directory:

1. Click **New Table** in your bucket
2. Configure upload:
   - **Name**: Table name (e.g., `customer`)
   - **File**: Select your CSV file (e.g., `customer.csv`)
3. Click **Upload**
4. Keboola will automatically:
   - Detect the `.csv.manifest` file
   - Set the primary key
   - Configure column types
   - Parse CSV correctly

### Step 4: Verify Upload

1. Click on the uploaded table
2. Check:
   - Row count matches expected
   - Primary key is set correctly
   - Columns look correct
   - Data preview shows correct values

**Repeat for all tables in your dataset.**

---

## Method 2: Keboola Storage API (Python)

### Step 1: Install Keboola Python Client

```bash
pip install kbcstorage
```

### Step 2: Create Upload Script

Save as `upload_to_keboola.py`:

```python
#!/usr/bin/env python3
"""Upload Datagen CSV exports to Keboola Connection."""

import os
import json
from pathlib import Path
from kbcstorage.client import Client

# Configuration
KEBOOLA_URL = "https://connection.keboola.com"
KEBOOLA_TOKEN = os.environ.get("KEBOOLA_TOKEN")  # Set via environment variable
CSV_DIR = "output_csv"  # Directory with CSV exports
BUCKET_NAME = "datagen"
BUCKET_STAGE = "in"  # 'in' for input data, 'out' for output data

def upload_to_keboola():
    """Upload all CSV files with manifests to Keboola."""

    if not KEBOOLA_TOKEN:
        print("❌ Error: KEBOOLA_TOKEN environment variable not set")
        print("Set it with: export KEBOOLA_TOKEN='your-token-here'")
        return 1

    # Initialize client
    print(f"📡 Connecting to Keboola...")
    client = Client(KEBOOLA_URL, KEBOOLA_TOKEN)

    # Create bucket if it doesn't exist
    bucket_id = f"{BUCKET_STAGE}.c-{BUCKET_NAME}"
    print(f"📦 Checking bucket: {bucket_id}")

    try:
        client.buckets.detail(bucket_id)
        print(f"✓ Bucket exists: {bucket_id}")
    except:
        print(f"Creating bucket: {bucket_id}")
        client.buckets.create(
            name=BUCKET_NAME,
            stage=BUCKET_STAGE,
            description="Synthetic data from Datagen"
        )
        print(f"✓ Created bucket: {bucket_id}")

    # Read dataset metadata
    dataset_meta_path = Path(CSV_DIR) / "dataset.json"
    if dataset_meta_path.exists():
        with open(dataset_meta_path) as f:
            dataset_meta = json.load(f)
        print(f"\n📋 Dataset: {dataset_meta['dataset_name']}")
        print(f"   Version: {dataset_meta['version']}")
        print(f"   Tables: {dataset_meta['generation_stats']['total_tables']}")
        print(f"   Rows: {dataset_meta['generation_stats']['total_rows']}")

    # Upload each CSV file
    csv_files = sorted(Path(CSV_DIR).glob("*.csv"))
    print(f"\n🔄 Uploading {len(csv_files)} tables...\n")

    uploaded = 0
    for csv_file in csv_files:
        table_name = csv_file.stem
        manifest_file = csv_file.parent / f"{csv_file.name}.manifest"

        # Read manifest for metadata
        primary_key = []
        if manifest_file.exists():
            with open(manifest_file) as f:
                manifest = json.load(f)
                primary_key = manifest.get("primary_key", [])

        print(f"  Uploading {table_name}...")

        try:
            # Check if table exists
            table_id = f"{bucket_id}.{table_name}"
            table_exists = False
            try:
                client.tables.detail(table_id)
                table_exists = True
            except:
                pass

            if table_exists:
                # Update existing table
                client.tables.load(
                    table_id=table_id,
                    file_path=str(csv_file),
                    is_incremental=False  # Full load
                )
                print(f"    ✓ Updated {table_name}")
            else:
                # Create new table
                client.tables.create(
                    name=table_name,
                    bucket_id=bucket_id,
                    file_path=str(csv_file),
                    primary_key=primary_key
                )
                print(f"    ✓ Created {table_name} (PK: {primary_key})")

            uploaded += 1

        except Exception as e:
            print(f"    ❌ Failed to upload {table_name}: {e}")

    print(f"\n✅ Upload complete!")
    print(f"   Uploaded: {uploaded}/{len(csv_files)} tables")
    print(f"   Bucket: {bucket_id}")
    print(f"   View at: {KEBOOLA_URL}/admin/projects/XXX/storage")

    return 0

if __name__ == "__main__":
    exit(upload_to_keboola())
```

### Step 3: Set Your Token

```bash
# Set Keboola token as environment variable
export KEBOOLA_TOKEN="your-storage-api-token-here"
```

To get your token:
1. Log in to Keboola Connection
2. Go to **Settings** → **API Tokens**
3. Create a new token or copy existing one
4. **Important**: Token must have **Storage** write permissions

### Step 4: Run Upload

```bash
# Make script executable
chmod +x upload_to_keboola.py

# Run upload
python upload_to_keboola.py
```

**Expected Output:**
```
📡 Connecting to Keboola...
📦 Checking bucket: in.c-datagen
✓ Bucket exists: in.c-datagen

📋 Dataset: BankSchema
   Version: 1.0
   Tables: 10
   Rows: 143098

🔄 Uploading 10 tables...

  Uploading branch...
    ✓ Created branch (PK: ['branch_id'])
  Uploading customer...
    ✓ Created customer (PK: ['customer_id'])
  ...

✅ Upload complete!
   Uploaded: 10/10 tables
   Bucket: in.c-datagen
```

---

## Method 3: Keboola CLI (Advanced)

### Step 1: Install Keboola CLI

The official Keboola CLI is written in Go:

```bash
# macOS (Homebrew)
brew install keboola/keboola-cli/kbc

# Linux/macOS (Direct download)
curl -s https://raw.githubusercontent.com/keboola/keboola-cli/main/scripts/install.sh | bash

# Windows (Chocolatey)
choco install keboola-cli

# Or download from GitHub releases:
# https://github.com/keboola/keboola-cli/releases
```

Verify installation:
```bash
kbc --version
```

### Step 2: Configure CLI

```bash
# Initialize configuration
kbc init

# Or configure manually
kbc config set api-host https://connection.keboola.com
kbc config set storage-api-token YOUR_TOKEN_HERE
```

### Step 3: Create Bucket

```bash
# Create bucket for datagen data
kbc create bucket in.c-datagen --name "Datagen Synthetic Data"
```

### Step 4: Upload Tables

```bash
cd output_csv

# Upload all tables
for csv in *.csv; do
  table_name="${csv%.csv}"
  echo "Uploading $table_name..."

  kbc push table in.c-datagen.$table_name \
    --file "$csv" \
    --incremental=false \
    --manifest "${csv}.manifest"
done
```

Or upload a single table:
```bash
kbc push table in.c-datagen.customer \
  --file customer.csv \
  --incremental=false \
  --manifest customer.csv.manifest
```

---

## Method 4: Automated Shell Script

### Create Upload Script

Save as `upload_datagen_to_keboola.sh`:

```bash
#!/bin/bash
# Upload Datagen exports to Keboola Connection
# Usage: ./upload_datagen_to_keboola.sh output_csv in.c-datagen

set -e

CSV_DIR="${1:-output_csv}"
BUCKET_ID="${2:-in.c-datagen}"
KEBOOLA_URL="${KEBOOLA_URL:-https://connection.keboola.com}"

# Check requirements
if [ -z "$KEBOOLA_TOKEN" ]; then
    echo "❌ Error: KEBOOLA_TOKEN environment variable not set"
    echo "Set it with: export KEBOOLA_TOKEN='your-token-here'"
    exit 1
fi

if [ ! -d "$CSV_DIR" ]; then
    echo "❌ Error: Directory $CSV_DIR does not exist"
    exit 1
fi

echo "📡 Uploading to Keboola Connection"
echo "   URL: $KEBOOLA_URL"
echo "   Bucket: $BUCKET_ID"
echo "   Source: $CSV_DIR"
echo ""

# Count CSV files
csv_count=$(find "$CSV_DIR" -name "*.csv" | wc -l)
echo "🔄 Found $csv_count CSV files to upload"
echo ""

# Read dataset metadata if available
if [ -f "$CSV_DIR/dataset.json" ]; then
    echo "📋 Dataset Metadata:"
    cat "$CSV_DIR/dataset.json" | python3 -m json.tool | grep -E "(dataset_name|total_tables|total_rows)" | sed 's/^/   /'
    echo ""
fi

# Upload using Python client
python3 - <<END_PYTHON
import os
import sys
from pathlib import Path
from kbcstorage.client import Client

csv_dir = "$CSV_DIR"
bucket_id = "$BUCKET_ID"
token = os.environ["KEBOOLA_TOKEN"]
url = "$KEBOOLA_URL"

client = Client(url, token)

# Ensure bucket exists
try:
    client.buckets.detail(bucket_id)
except:
    print(f"Creating bucket: {bucket_id}")
    stage, name = bucket_id.split(".c-")
    client.buckets.create(name=name, stage=stage)

# Upload tables
uploaded = 0
for csv_file in sorted(Path(csv_dir).glob("*.csv")):
    table_name = csv_file.stem
    table_id = f"{bucket_id}.{table_name}"

    print(f"  ⬆️  {table_name}...", end=" ", flush=True)

    try:
        # Try to update existing table
        client.tables.detail(table_id)
        client.tables.load(table_id=table_id, file_path=str(csv_file), is_incremental=False)
        print("✓ updated")
    except:
        # Create new table
        client.tables.create(name=table_name, bucket_id=bucket_id, file_path=str(csv_file))
        print("✓ created")

    uploaded += 1

print(f"\n✅ Uploaded {uploaded} tables to {bucket_id}")
END_PYTHON

echo ""
echo "🎉 Upload complete!"
echo "   View at: $KEBOOLA_URL/admin/projects/YOUR_PROJECT/storage"
```

### Make Executable and Run

```bash
chmod +x upload_datagen_to_keboola.sh

export KEBOOLA_TOKEN="your-token-here"

./upload_datagen_to_keboola.sh output_csv in.c-datagen
```

---

## Method 5: Direct API Calls (curl)

For complete control, use the Keboola Storage API directly:

### Step 1: Get Bucket ID

```bash
export KEBOOLA_TOKEN="your-token-here"
export KEBOOLA_URL="https://connection.keboola.com"

# List all buckets
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  "$KEBOOLA_URL/v2/storage/buckets"
```

### Step 2: Create Table

```bash
# Create table in bucket
curl -X POST \
  -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  -F "name=customer" \
  -F "dataFile=@output_csv/customer.csv" \
  -F "primaryKey[]=customer_id" \
  "$KEBOOLA_URL/v2/storage/buckets/in.c-datagen/tables-async"
```

### Step 3: Update Table Data

```bash
# Update existing table
curl -X POST \
  -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  -F "dataFile=@output_csv/customer.csv" \
  -F "incremental=0" \
  "$KEBOOLA_URL/v2/storage/tables/in.c-datagen.customer/import-async"
```

---

## Complete Workflow Examples

### Example 1: Generate and Upload Bank Data

```bash
# 1. Generate synthetic data
datagen generate example/bank.json -o output_bank --seed 42

# 2. Export to CSV with Keboola metadata
datagen export example/bank.json --data-dir output_bank -o output_csv

# 3. Set Keboola token
export KEBOOLA_TOKEN="your-token-here"

# 4. Upload using Python script
python upload_to_keboola.py

# 5. Verify in Keboola UI
# Go to: https://connection.keboola.com → Storage → in.c-datagen
```

### Example 2: CI/CD Pipeline

```bash
#!/bin/bash
# .github/workflows/generate-and-upload.sh

set -e

# Generate fresh data
datagen generate schemas/production.json -o /tmp/output --seed $(date +%s)

# Validate quality
datagen validate schemas/production.json --data-dir /tmp/output

# Export to CSV
datagen export schemas/production.json --data-dir /tmp/output -o /tmp/csv

# Upload to Keboola
export KEBOOLA_TOKEN="${KEBOOLA_STORAGE_TOKEN}"  # From CI secrets
python scripts/upload_to_keboola.py /tmp/csv in.c-synthetic-data

# Cleanup
rm -rf /tmp/output /tmp/csv

echo "✅ Synthetic data refreshed in Keboola"
```

### Example 3: Multiple Schemas

```bash
# Generate and upload multiple datasets
for schema in schemas/*.json; do
  name=$(basename "$schema" .json)

  echo "Processing $name..."

  # Generate
  datagen generate "$schema" -o "output_${name}" --seed 42

  # Export
  datagen export "$schema" --data-dir "output_${name}" -o "csv_${name}"

  # Upload to separate buckets
  python upload_to_keboola.py "csv_${name}" "in.c-${name}"

  echo "✓ Uploaded $name to in.c-${name}"
done

echo "🎉 All schemas uploaded!"
```

---

## Troubleshooting

### Issue: "Invalid token"

**Solution:**
```bash
# Verify token is set
echo $KEBOOLA_TOKEN

# Test token
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  https://connection.keboola.com/v2/storage/tokens/verify
```

### Issue: "Bucket not found"

**Solution:**
```bash
# List all buckets
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  https://connection.keboola.com/v2/storage/buckets

# Create bucket if needed
curl -X POST \
  -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  -d "name=datagen" \
  -d "stage=in" \
  https://connection.keboola.com/v2/storage/buckets
```

### Issue: "Table already exists"

**Solution:**
```bash
# Update existing table instead of creating
# In Python client:
client.tables.load(
    table_id="in.c-datagen.customer",
    file_path="customer.csv",
    is_incremental=False  # Full reload
)
```

### Issue: "Primary key violation"

**Solution:**
```bash
# Check for duplicate IDs in your data
python3 -c "
import pandas as pd
df = pd.read_csv('output_csv/customer.csv')
print('Total rows:', len(df))
print('Unique customer_ids:', df['customer_id'].nunique())
print('Duplicates:', len(df) - df['customer_id'].nunique())
"

# Regenerate with different seed if needed
datagen generate schema.json -o output --seed 43
```

### Issue: "Module 'kbcstorage' not found"

**Solution:**
```bash
# Install Keboola Python client
pip install kbcstorage

# Or with specific version
pip install kbcstorage==1.1.1

# Verify installation
python3 -c "import kbcstorage; print(kbcstorage.__version__)"
```

---

## Best Practices

### 1. Use Environment Variables for Tokens

```bash
# Never hardcode tokens
export KEBOOLA_TOKEN="your-token-here"

# Or use a .env file (don't commit it!)
echo "KEBOOLA_TOKEN=your-token-here" > .env
source .env
```

### 2. Organize Buckets

```
in.c-datagen-dev      # Development data
in.c-datagen-staging  # Staging/QA data
in.c-datagen-prod     # Production synthetic data
```

### 3. Add Descriptions

```python
# In Python script
client.buckets.create(
    name="datagen",
    stage="in",
    description=f"Synthetic data generated {datetime.now().isoformat()}"
)
```

### 4. Verify After Upload

```bash
# Count rows in Keboola
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  "https://connection.keboola.com/v2/storage/tables/in.c-datagen.customer" \
  | jq '.rowsCount'

# Compare with local CSV
wc -l output_csv/customer.csv
```

### 5. Automate Regular Refreshes

```bash
# Cron job to refresh data daily
0 2 * * * /usr/local/bin/refresh_synthetic_data.sh
```

---

## Summary

**Recommended Methods by Use Case:**

| Use Case | Method | Why |
|----------|--------|-----|
| **One-time upload** | Manual UI | Simplest, visual feedback |
| **Regular uploads** | Python script | Automated, repeatable |
| **CI/CD pipeline** | Shell script | Integrates with builds |
| **Complex workflows** | Keboola CLI | Full featured, official tool |
| **Custom integration** | Direct API | Maximum control |

**Typical Workflow:**
```bash
# Generate → Export → Upload
datagen generate schema.json -o output --seed 42
datagen export schema.json --data-dir output -o csv_export
python upload_to_keboola.py
```

**All methods produce the same result**: Your synthetic data tables in Keboola Connection, ready for use in transformations, analyses, and applications!

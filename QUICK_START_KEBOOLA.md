# Quick Start: Datagen → Keboola

Upload synthetic data to Keboola Connection in 3 steps.

---

## Quick Start (5 minutes)

### 1. Generate & Export Data

```bash
# Generate synthetic data
datagen generate example/bank.json -o output_bank --seed 42

# Export to CSV with Keboola metadata
datagen export example/bank.json --data-dir output_bank -o output_csv
```

### 2. Get Your Keboola Credentials

You need **2 things**:

**A) Endpoint URL** - Where you access Keboola
- US: `https://connection.keboola.com`
- EU: `https://connection.eu-central-1.keboola.com`
- (Use whatever URL you use to log in)

**B) Storage API Token** - Authentication
1. Log in to your Keboola endpoint
2. Go to **Settings** → **API Tokens**
3. Click **New Token**
4. Enable **Storage** read/write permissions
5. Copy your token (you won't see it again!)

### 3. Upload to Keboola

**Option A: Python Script (Recommended)**

```bash
# Install client
pip install kbcstorage

# Set credentials
export KEBOOLA_URL="https://connection.keboola.com"  # Your endpoint
export KEBOOLA_TOKEN="your-token-here"               # Your token

# Upload
python scripts/upload_to_keboola.py output_csv
```

**Option B: Manual Upload**

1. Log in to Keboola Connection
2. Go to **Storage** → **Tables**
3. Create bucket: `datagen`
4. Upload each `*.csv` file (manifests auto-detected)

**Done!** Your data is now in Keboola.

---

## Commands Reference

```bash
# Generate data
datagen generate <schema.json> -o <output_dir> --seed <seed>

# Export to CSV
datagen export <schema.json> --data-dir <output_dir> -o <csv_dir>

# Upload to Keboola
python scripts/upload_to_keboola.py <csv_dir> [bucket_name]
```

---

## Example: Bank Schema

```bash
# Complete workflow
datagen generate example/bank.json -o output_bank --seed 42
datagen export example/bank.json --data-dir output_bank -o output_csv
export KEBOOLA_TOKEN="your-token"
python scripts/upload_to_keboola.py output_csv
```

**Result**: 10 tables with 143K rows uploaded to Keboola bucket `in.c-datagen`

---

## Files Created

```
output_csv/
├── dataset.json              # Dataset metadata
├── customer.csv              # Table data
├── customer.csv.manifest     # Keboola manifest (PK, columns)
├── account.csv
├── account.csv.manifest
└── ... (one CSV + manifest per table)
```

---

## Troubleshooting

**"KEBOOLA_TOKEN not set"**
```bash
export KEBOOLA_URL="https://connection.keboola.com"  # Your region
export KEBOOLA_TOKEN="your-token-here"
```

**"Which endpoint do I use?"**
- Use the URL you see when you log in to Keboola
- Common: `https://connection.keboola.com` (US)
- Or: `https://connection.eu-central-1.keboola.com` (EU)

**"Where do I get a token?"**
- Keboola UI → Settings → API Tokens → New Token
- Enable Storage read/write permissions
- See `KEBOOLA_CREDENTIALS.md` for detailed guide

**"kbcstorage not found"**
```bash
pip install kbcstorage
```

**"Bucket not found"**
- Script creates bucket automatically
- Or create manually in Keboola UI

---

## Full Documentation

- **Export Guide**: See `EXPORT_GUIDE.md`
- **Keboola Upload**: See `KEBOOLA_UPLOAD.md`
- **Implementation**: See `EXPORT_SUMMARY.md`

---

## Support

- Keboola docs: https://help.keboola.com/
- Datagen issues: https://github.com/your-org/datagen/issues
- Python client: https://github.com/keboola/python-storage-api-client

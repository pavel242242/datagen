# SÚKL Extractor - Keboola Setup Guide

## Using Existing "Custom Python" Component

This guide shows how to configure SÚKL extractor using Keboola's existing Python extractor component (no Docker needed).

---

## Step 1: Find Custom Python Component

In your Keboola project:

1. Go to **Components** or **Extractors**
2. Search for: **"Python"** or **"Custom Python"**
3. Look for components like:
   - "Python Transformation"
   - "Generic Python"
   - "Custom Python Extractor"

---

## Step 2: Create New Configuration

1. Click **+ New Configuration**
2. Name it: `SUKL Data Extractor`
3. Description: `AI-powered extraction from opendata.sukl.cz`

---

## Step 3: Configure Code

### Option A: Paste Code Directly

Copy the entire contents of `sukl_extractor_simple.py` into the code editor.

### Option B: Upload File

Upload `sukl_extractor_simple.py` as the main script.

---

## Step 4: Set Environment Variables

In the component configuration, add these environment variables:

```json
{
  "ANTHROPIC_API_KEY": "sk-ant-YOUR-KEY-HERE",
  "KBC_TOKEN": "YOUR-KEBOOLA-TOKEN",
  "KBC_URL": "https://connection.us-east4.gcp.keboola.com/",
  "DATASET": "dlp"
}
```

### Where to get these:

**ANTHROPIC_API_KEY**
- Get from: https://console.anthropic.com/
- Example: `sk-ant-api03-xxx...`

**KBC_TOKEN**
- In Keboola: Settings → API Tokens → New Token
- Enable: Storage (read + write)
- Example: `2929-1172770-xxx...`

**KBC_URL**
- Your Keboola instance URL
- US East: `https://connection.us-east4.gcp.keboola.com/`
- EU: `https://connection.eu-central-1.keboola.com/`

**DATASET**
- Which dataset to extract
- Options: `dlp`, `pharmacies`, `lek13`, `dis13`
- Start with: `dlp`

---

## Step 5: Install Dependencies

In the component configuration, specify requirements:

```
anthropic>=0.39.0
kbcstorage>=0.9.0
pandas>=2.0.0
requests>=2.31.0
```

Or if using `requirements.txt`:
```bash
anthropic
kbcstorage
pandas
requests
```

---

## Step 6: Test Run

1. Click **Run Component**
2. Watch the logs for:
   ```
   🌐 Fetching catalog...
   🤖 Using AI to find download link...
   ✓ Found: https://opendata.sukl.cz/...
   📥 Downloading...
   ✓ Downloaded: 8.85 MB
   📦 Extracting ZIP...
   Found 30 CSV files
   ✓ Created: dlp_lecivepripravky (18,234 rows)
   ...
   ✅ Extraction complete!
   ```

3. Check Storage: `in.c-sukl` bucket should contain ~30 tables

---

## Step 7: Run Other Datasets

To extract other datasets, create separate configurations or modify the `DATASET` env var:

| DATASET Value | Description | Tables Created |
|---------------|-------------|----------------|
| `dlp` | Medicines Database | ~30 tables |
| `pharmacies` | Pharmacy List | ~1 table |
| `lek13` | Dispensing Reports | ~1 table |
| `dis13` | Distribution Reports | ~1 table |

---

## Step 8: Schedule Weekly Updates

1. Go to **Orchestrations**
2. Create new: **SÚKL Weekly Update**
3. Add your SÚKL extractor configurations
4. Schedule:
   ```
   Cron: 0 2 * * 1
   (Every Monday at 2 AM)
   ```
5. Enable orchestration

---

## Expected Output

### in.c-sukl bucket will contain:

**DLP Dataset (30 tables):**
- `dlp_lecivepripravky` - All medicines (~18,000 rows)
- `dlp_latky` - Active ingredients (~4,000 rows)
- `dlp_organizace` - Companies (~1,500 rows)
- `dlp_atc` - ATC codes (~6,000 rows)
- `dlp_slozeni` - Composition (~25,000 rows)
- ... and 25 more tables

**Pharmacies:**
- `pharmacies_lekarny` - All pharmacies (~2,500 rows)

**LEK-13:**
- `lek13_*` - Monthly dispensing data

**DIS-13:**
- `dis13_*` - Monthly distribution data

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
→ Check environment variables in component config

### "KBC_TOKEN not set"
→ Verify token is set and has Storage permissions

### "Could not find download URL"
→ Check if SÚKL website is accessible
→ Verify Anthropic API key is valid

### "Bucket permission denied"
→ Regenerate Keboola token with Storage write permission

### Import errors (anthropic, kbcstorage)
→ Ensure dependencies are installed (requirements.txt)

---

## Cost Estimate

**Anthropic API:**
- Per run (DLP): ~$0.01
- Per run (all datasets): ~$0.05
- Monthly (weekly runs): ~$0.20

**Keboola:**
- Storage: ~50 MB per dataset
- Depends on your plan

**Total: < $1/month**

---

## Next Steps

1. ✅ Copy `sukl_extractor_simple.py` code
2. ⏳ Paste into Keboola Custom Python component
3. ⏳ Set environment variables (API keys)
4. ⏳ Run test with DLP dataset
5. ⏳ Create configs for other datasets
6. ⏳ Setup weekly orchestration

---

## Files

- `sukl_extractor_simple.py` - Main extraction script (paste this into Keboola)
- `requirements.txt` - Python dependencies
- This file - Setup instructions

---

**Ready?** Copy the Python code and paste it into your Keboola Custom Python component!

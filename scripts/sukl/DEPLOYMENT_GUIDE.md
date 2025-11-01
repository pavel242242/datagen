# SÚKL Component - Deployment Guide

## What We Built

**AI-powered Keboola component** that automatically extracts Czech pharmaceutical open data from SÚKL.

### Key Features:
- ✅ Claude AI finds latest download URLs automatically
- ✅ Handles 5 different datasets (medicines, pharmacies, prescriptions, etc.)
- ✅ Converts Czech encoding to UTF-8
- ✅ Loads directly into your Keboola project
- ✅ Runs on schedule (weekly)

---

## Deployment Options

### Option A: Docker Container (Recommended)

Run as a containerized component in Keboola.

**Steps:**

1. **Build Docker image** (if you have Docker):
```bash
cd scripts/sukl/component/
docker build -t sukl-extractor .
```

2. **Push to registry** (requires Docker registry):
```bash
# Tag for your registry
docker tag sukl-extractor YOUR_REGISTRY/sukl-extractor:latest

# Push
docker push YOUR_REGISTRY/sukl-extractor:latest
```

3. **Register in Keboola**:
   - Navigate to: **Components → Developer Portal → Register Component**
   - Enter your Docker image URI
   - Upload `component.json` configuration
   - Save

### Option B: Python Transformation (Simpler, No Docker)

Run as a Python transformation directly in Keboola UI.

**Steps:**

1. Go to **Transformations** → **New Transformation** → **Python**

2. Upload `component/component.py` code

3. Add configuration:
```json
{
  "parameters": {
    "datasets": ["dlp"],
    "bucket_id": "in.c-sukl"
  },
  "#anthropic_api_key": "YOUR_KEY",
  "#kbc_token": "YOUR_KEBOOLA_TOKEN"
}
```

4. Install dependencies:
```python
!pip install anthropic kbcstorage pandas requests
```

5. Run transformation

---

## Required Credentials

### 1. Anthropic API Key

**Get it here:** https://console.anthropic.com/

1. Sign up / Log in
2. Go to **API Keys**
3. Click **Create Key**
4. Copy the key (starts with `sk-ant-...`)

**Cost:** ~$0.05 per full run (5 datasets)

### 2. Keboola Storage Token

**Get it here:** Your Keboola Project

1. Go to **Settings** → **API Tokens**
2. Click **New Token**
3. Name it: `SÚKL Extractor`
4. Enable: **Storage** (read + write)
5. Copy the token

---

## Configuration

### In Keboola UI

Once component is deployed, configure:

**1. Datasets to Extract:**
- ☑ DLP (Medicines Database) - ~30 tables
- ☑ Pharmacies - 1 table
- ☑ LEK-13 (Dispensing) - monthly data
- ☑ DIS-13 (Distribution) - monthly data
- ☑ eRecept (Prescriptions) - monthly data

**2. Storage Bucket:**
- Default: `in.c-sukl`
- Will be created automatically if doesn't exist

**3. Credentials:**
- Anthropic API Key: Your Claude API key
- Keboola Token: Storage API token

---

## Initial Run

### Test with DLP Dataset First

1. Configure component
2. Select **only DLP** dataset
3. Click **Run Component**
4. Wait ~5 minutes

**Expected Result:**
- ~30 tables created in `in.c-sukl` bucket
- Table names: `dlp_lecivepripravky`, `dlp_latky`, `dlp_organizace`, etc.
- Total rows: ~50,000+ across all tables

### Then Run All Datasets

1. Select all 5 datasets
2. Run component
3. Wait ~15-20 minutes

**Expected Result:**
- ~40+ tables total
- All SÚKL open data loaded

---

## Scheduling

### Setup Weekly Updates

1. Go to **Orchestrations**
2. Create new: **SÚKL Weekly Update**
3. Add this component
4. Schedule: **Every Monday at 2 AM**
   ```
   Cron: 0 2 * * 1
   ```
5. Enable orchestration

**Why Monday?**
- SÚKL publishes updates on 26th of each month
- Weekly check ensures we catch new files
- AI will find latest version automatically

---

## What Gets Loaded

### DLP - Medicines Database (~30 tables)

| Table | Description | Rows |
|-------|-------------|------|
| `dlp_lecivepripravky` | All registered medicines | ~18,000 |
| `dlp_latky` | Active ingredients | ~4,000 |
| `dlp_organizace` | Pharmaceutical companies | ~1,500 |
| `dlp_atc` | ATC classification | ~6,000 |
| `dlp_slozeni` | Composition | ~25,000 |
| ... | 25 more tables | ... |

### Pharmacies

| Table | Description | Rows |
|-------|-------------|------|
| `pharmacies_lekarny` | All Czech pharmacies | ~2,500 |

### LEK-13 - Dispensing Reports

| Table | Description | Rows |
|-------|-------------|------|
| `lek13_*` | Monthly pharmacy dispensing | ~50,000/month |

### DIS-13 - Distribution

| Table | Description | Rows |
|-------|-------------|------|
| `dis13_*` | Monthly distribution data | ~30,000/month |

### eRecept - Prescriptions

| Table | Description | Rows |
|-------|-------------|------|
| `erecept_*` | Electronic prescription data | ~100,000/month |

---

## Monitoring

### Check Logs

- Go to component run
- View **Logs** tab
- Look for:
  - ✓ "Found URL: ..."
  - ✓ "Downloaded: X.XX MB"
  - ✓ "Created: table_name"

### Common Issues

**"AI could not find download URL"**
- SÚKL website might be down
- Page structure changed (rare)
- Anthropic API key issue

**"Failed to convert CSV"**
- Some CSVs have formatting issues
- Non-critical - other files still upload
- Check logs for which files failed

**"Bucket permission denied"**
- Keboola token needs Storage write permission
- Regenerate token with correct permissions

---

## Cost Breakdown

### Anthropic API
- **Per run:** ~$0.05 (5 datasets)
- **Monthly:** ~$0.20 (4 weekly runs)
- **Annual:** ~$2.40

### Keboola Storage
- **Data volume:** ~50 MB per run
- **Total storage:** ~200 MB
- **Cost:** Depends on your plan

**Total monthly cost:** < $1

---

## Next Steps

1. ✅ Component is built (in `scripts/sukl/component/`)
2. ⏳ Deploy to Keboola (choose Option A or B)
3. ⏳ Configure credentials
4. ⏳ Test with DLP dataset
5. ⏳ Run full extraction
6. ⏳ Setup weekly schedule

---

## Support

- **SÚKL Data Issues:** opendata@sukl.gov.cz
- **Keboola Support:** support@keboola.com
- **Component Code:** `scripts/sukl/component/`

---

**Ready to deploy?** Choose your deployment option and follow the steps above!

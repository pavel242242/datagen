# SÚKL Open Data Extractor - Keboola Component

AI-powered extraction of Czech pharmaceutical open data from SÚKL (State Institute for Drug Control).

## Features

- 🤖 **AI-Powered URL Discovery**: Uses Claude AI to automatically find the latest download links
- 📊 **Multiple Datasets**: Extracts medicines database, pharmacies, prescriptions, dispensing, and distribution data
- 🔄 **Automatic Updates**: Detects new files without manual URL updates
- 🌐 **Encoding Conversion**: Handles Czech encoding (win-1250) and converts to UTF-8
- ☁️ **Direct to Keboola**: Loads data directly into Keboola Storage

## Available Datasets

| Dataset | Description | Update Frequency | Tables |
|---------|-------------|------------------|--------|
| **DLP** | Medicines Database | Monthly | ~30 tables with medicine details, active ingredients, organizations |
| **Pharmacies** | Pharmacy List | Monthly | 1 table with all licensed pharmacies |
| **LEK-13** | Dispensing Reports | Monthly | Pharmacy dispensing statistics |
| **DIS-13** | Distribution Reports | Monthly | Distribution from authorized distributors |
| **eRecept** | Electronic Prescriptions | Monthly | Prescription and dispensation data by district |

## Installation

### Option 1: Deploy as Private Component (Recommended)

1. **Build Docker image**:
```bash
cd component/
docker build -t sukl-extractor .
```

2. **Push to your registry**:
```bash
docker tag sukl-extractor your-registry/sukl-extractor:latest
docker push your-registry/sukl-extractor:latest
```

3. **Register in Keboola**:
   - Go to Components → Register New Component
   - Enter image URI
   - Upload `component.json` configuration

### Option 2: Run in Generic Docker Runner

1. Go to **Transformations** → **Generic Docker**
2. Upload `component.py` and `requirements.txt`
3. Configure credentials
4. Run

## Configuration

### Required Credentials

**Anthropic API Key**
- Get from: https://console.anthropic.com/
- Permissions: API access
- Used for: Intelligent URL discovery from catalog pages

**Keboola Storage Token**
- Create in: Keboola → Settings → API Tokens
- Permissions: Storage read/write
- Used for: Uploading data to Storage

### Parameters

**Datasets** (multiselect)
- Select which datasets to extract
- Default: `dlp` (Medicines Database)
- Options: `dlp`, `pharmacies`, `lek13`, `dis13`, `erecept`

**Bucket ID** (string)
- Storage bucket where data will be loaded
- Default: `in.c-sukl`
- Will be created if doesn't exist

## Usage

### Manual Run

1. Navigate to your component configuration
2. Set credentials (Anthropic API key, Keboola token)
3. Select datasets to extract
4. Click **Run Component**

### Scheduled Run

1. Go to **Orchestrations**
2. Create new orchestration
3. Add this component
4. Set schedule (recommended: **Weekly on Mondays**)
5. Enable orchestration

## How It Works

```
┌─────────────────────────────────────────────────┐
│  1. Fetch SÚKL Catalog Page                     │
│     https://opendata.sukl.cz/?q=katalog/...     │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  2. AI Analyzes HTML → Finds Latest Download URL│
│     Claude 3.5 Sonnet extracts direct link      │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  3. Download ZIP/CSV File                       │
│     Saves to temporary directory                │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  4. Extract & Convert                           │
│     • Unzip archives                            │
│     • Convert encoding (win-1250 → UTF-8)       │
│     • Change delimiter (semicolon → comma)      │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  5. Upload to Keboola Storage                   │
│     Creates/updates tables in bucket            │
└─────────────────────────────────────────────────┘
```

## Output Tables

All tables are prefixed with dataset key:

**DLP Dataset** → `in.c-sukl.dlp_*`
- `dlp_lecivepripravky` - Medicines
- `dlp_latky` - Active ingredients
- `dlp_organizace` - Organizations
- `dlp_atc` - ATC classification
- ... (~30 tables total)

**Pharmacies** → `in.c-sukl.pharmacies_*`
- `pharmacies_lekarny` - Pharmacy list

**LEK-13** → `in.c-sukl.lek13_*`
- Monthly dispensing data

**DIS-13** → `in.c-sukl.dis13_*`
- Monthly distribution data

**eRecept** → `in.c-sukl.erecept_*`
- Prescription and dispensation data

## Data Sources

All data is from **SÚKL** (Státní ústav pro kontrolu léčiv):
- Portal: https://opendata.sukl.cz/
- Contact: opendata@sukl.gov.cz
- License: Open Data (freely usable)

## Troubleshooting

### "AI could not find download URL"

- Check if SÚKL catalog page structure changed
- Verify Anthropic API key is valid
- Check if dataset is still available on SÚKL portal

### "Failed to convert CSV"

- Some CSV files may have inconsistent structure
- Component logs which files failed (non-critical)
- Successfully converted files are still uploaded

### "Bucket not found"

- Ensure Keboola token has Storage write permissions
- Component will try to create bucket automatically

## Cost Estimation

**Anthropic API**:
- ~$0.01 per dataset (Sonnet 3.5)
- Full run (5 datasets): ~$0.05
- Monthly cost (4 runs): ~$0.20

**Keboola**:
- Depends on your plan
- Data volume: ~50 MB per run
- Storage: ~200 MB total

## Development

**Local Testing**:
```bash
export ANTHROPIC_API_KEY="your-key"
export KEBOOLA_URL="your-url"
export KEBOOLA_TOKEN="your-token"

python component.py
```

**Docker Testing**:
```bash
docker run -it \
  -e ANTHROPIC_API_KEY="your-key" \
  -e KBC_URL="your-url" \
  -e KBC_TOKEN="your-token" \
  -v $(pwd)/data:/data \
  sukl-extractor
```

## Support

- Issues: [GitHub Issues](https://github.com/your-org/sukl-extractor/issues)
- SÚKL Data Questions: opendata@sukl.gov.cz
- Keboola Support: support@keboola.com

## License

MIT License - See LICENSE file

---

**Built with Claude AI** 🤖

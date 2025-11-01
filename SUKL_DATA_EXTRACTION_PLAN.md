# SÚKL Data Extraction & Keboola Integration Plan

## Overview
Extract all available data from SÚKL (State Institute for Drug Control) and load into Keboola with weekly updates.

---

## 📊 Available Datasets

### 1. **DLP - Medicines Database** (Priority: HIGH)
- **URL**: https://opendata.sukl.cz/soubory/SOD20250926/DLP20250926.zip
- **Format**: ZIP containing multiple CSV files (win-1250 encoding)
- **Size**: ~9.28 MB
- **Update**: Monthly (26th of each month)
- **Content**:
  - Registered medicines
  - Special therapeutic programs
  - Foods for special medical purposes
  - Multiple related tables (need to inspect ZIP)
- **Data Interface**: Column descriptions available as separate CSV

### 2. **Pharmacy List** (Priority: HIGH)
- **URL**: https://opendata.sukl.cz/soubory/SOD20250926/LEKARNY20250926.zip
- **Format**: ZIP with CSV (win-1250 encoding)
- **Size**: ~239 KB
- **Update**: Monthly (26th)
- **Content**: Complete list of pharmacies in Czech Republic

### 3. **LEK-13 - Pharmacy Dispensing Reports** (Priority: HIGH)
- **URL**: https://opendata.sukl.cz/soubory/LEK13/LEK13_2024/LEK13_2024.zip
- **Format**: ZIP with monthly CSV files (win-1250 encoding)
- **Size**: ~3.41 MB
- **Update**: Monthly
- **Content**:
  - Monthly summary of medicine dispensing
  - Pharmacy reports
  - Price and reimbursement information

### 4. **DIS-13 - Distribution Reports** (Priority: HIGH)
- **URL**: https://opendata.sukl.cz/soubory/DIS13/DIS13_202509v01.csv
- **Format**: Individual CSV files per month (win-1250 encoding)
- **Size**: ~2.08 MB per month
- **Update**: Monthly
- **Content**:
  - Medicine distribution data
  - Authorized distributor reports
  - Supply chain information

### 5. **eRecept - Electronic Prescriptions** (Priority: HIGH)
- **URLs**:
  - Prescriptions: https://opendata.sukl.cz/soubory/ERECEPT/erecept_predpis_202509.zip
  - Dispensations: https://opendata.sukl.cz/soubory/ERECEPT/erecept_vydej_202509.zip
- **Format**: ZIP with CSV (UTF-8 encoding)
- **Size**: 6.5 MB + 5.2 MB
- **Update**: Monthly
- **Content**:
  - Anonymized aggregated prescription data
  - Dispensing data by district
  - Package quantities

### 6. **Medical Devices Registry (RZPRO)** (Priority: MEDIUM)
- **Portal**: https://eregpublicsecure.ksrzis.cz/Registr/RZPRO/OpenData
- **Format**: Multiple CSV files (UTF-8 encoding)
- **Update**: Daily
- **Content**:
  - Registered persons/entities
  - Notified medical devices
  - Device manufacturers
  - Device variants

### 7. **Product Documentation** (Priority: LOW)
- **SPC** (Summary of Product Characteristics): PDF/DOC files
- **PIL** (Package Inserts): PDF/DOC files
- **Package Texts**: PDF/DOC files
- **Update**: Monthly
- **Note**: Large document files, may skip initially

---

## 🎯 Implementation Plan

### Phase 1: Initial Data Load (Week 1)

#### Step 1.1: Setup Infrastructure
- [ ] Create Python extraction scripts in `/scripts/sukl/`
- [ ] Add configuration file for SÚKL sources
- [ ] Setup logging and error handling
- [ ] Create Keboola bucket: `in.c-sukl`

#### Step 1.2: Extract & Load Core Datasets
1. **DLP - Medicines Database**
   - Download ZIP
   - Extract all CSVs
   - Convert from win-1250 to UTF-8
   - Map to Keboola tables
   - Upload to `in.c-sukl.dlp_*`

2. **Pharmacy List**
   - Download ZIP
   - Extract CSV
   - Convert encoding
   - Upload to `in.c-sukl.pharmacies`

3. **LEK-13 Dispensing**
   - Download annual ZIP
   - Extract monthly CSVs
   - Upload to `in.c-sukl.lek13_dispensing`

4. **DIS-13 Distribution**
   - Download latest CSV
   - Upload to `in.c-sukl.dis13_distribution`

5. **eRecept Data**
   - Download both ZIPs (prescriptions + dispensations)
   - Extract and upload to separate tables
   - `in.c-sukl.erecept_prescriptions`
   - `in.c-sukl.erecept_dispensations`

### Phase 2: Medical Devices (Week 1-2)

#### Step 2.1: RZPRO Integration
- [ ] Explore RZPRO open data portal structure
- [ ] Download all CSV files
- [ ] Map to Keboola tables
- [ ] Upload to `in.c-sukl.rzpro_*`

### Phase 3: Weekly Update Automation (Week 2)

#### Step 3.1: Create Update Script
```python
scripts/sukl/weekly_update.py
- Check for new files (date-based URLs)
- Download only if newer than last run
- Track last update timestamp
- Incremental vs full refresh logic
```

#### Step 3.2: Update Strategy by Dataset

| Dataset | Strategy | Reason |
|---------|----------|--------|
| DLP | Full refresh | Monthly, relatively small |
| Pharmacies | Full refresh | Monthly, very small |
| LEK-13 | Append new month | Historical data |
| DIS-13 | Append new month | Historical data |
| eRecept | Append new month | Historical data |
| RZPRO | Full refresh | Daily updates, current state |

#### Step 3.3: Scheduling Options
**Option A: Cron Job**
```bash
0 2 * * 1  cd /path/to/datagen && ./scripts/sukl/weekly_update.sh
```

**Option B: Keboola Orchestration**
- Create component/script in Keboola
- Schedule weekly run
- Better monitoring & logging

**Option C: GitHub Actions** (Recommended)
- Version controlled
- Free for public repos
- Easy monitoring
- Can notify on failures

### Phase 4: Data Quality & Monitoring (Week 2-3)

#### Step 4.1: Validation
- [ ] Row count checks
- [ ] Schema validation
- [ ] Date continuity checks
- [ ] Encoding verification

#### Step 4.2: Monitoring
- [ ] Upload success/failure alerts
- [ ] Data freshness checks
- [ ] Size anomaly detection
- [ ] Email notifications

---

## 🛠️ Technical Architecture

### Script Structure
```
scripts/sukl/
├── config.json              # Source URLs, encodings, table mappings
├── extractor.py            # Download & extraction logic
├── transformer.py          # Encoding conversion, data cleaning
├── loader.py               # Keboola upload
├── weekly_update.py        # Orchestration script
├── utils.py                # Helper functions
└── requirements.txt        # Dependencies
```

### Key Dependencies
```
requests          # HTTP downloads
kbcstorage       # Keboola client (already installed)
python-dotenv    # Credentials (already installed)
chardet          # Encoding detection
pandas           # Data manipulation
```

### Configuration Example
```json
{
  "datasets": {
    "dlp": {
      "url_pattern": "https://opendata.sukl.cz/soubory/SOD{date}/DLP{date}.zip",
      "date_format": "%Y%m%d",
      "encoding": "cp1250",
      "update_frequency": "monthly",
      "update_day": 26,
      "keboola_bucket": "in.c-sukl",
      "table_prefix": "dlp_"
    }
  }
}
```

---

## 📅 Timeline

| Week | Tasks | Deliverable |
|------|-------|-------------|
| 1 | Phase 1: Initial load of 5 core datasets | All current data in Keboola |
| 1-2 | Phase 2: Medical devices integration | RZPRO data loaded |
| 2 | Phase 3: Weekly automation script | Working update script |
| 2-3 | Phase 4: Monitoring & alerts | Production-ready pipeline |

---

## 🚨 Challenges & Solutions

### Challenge 1: Multiple Encodings
- **Issue**: win-1250 vs UTF-8
- **Solution**: Auto-detect and convert during extraction

### Challenge 2: Date-based URLs
- **Issue**: Need to guess current file names
- **Solution**: Try multiple date patterns, fallback logic

### Challenge 3: ZIP File Structures
- **Issue**: Unknown CSV structure inside ZIPs
- **Solution**: Download sample, inspect, document schemas

### Challenge 4: Historical Data
- **Issue**: Do we load all history or just current?
- **Solution**:
  - Initial load: Latest only
  - Then: Append new months incrementally

### Challenge 5: RZPRO Different Portal
- **Issue**: Medical devices on different domain
- **Solution**: Separate extraction module

---

## 💾 Expected Data Volume

| Dataset | Frequency | Size/Month | Annual Size |
|---------|-----------|------------|-------------|
| DLP | Monthly | 9 MB | 108 MB |
| Pharmacies | Monthly | 0.2 MB | 2.4 MB |
| LEK-13 | Monthly | 0.3 MB | 3.6 MB |
| DIS-13 | Monthly | 2 MB | 24 MB |
| eRecept | Monthly | 12 MB | 144 MB |
| RZPRO | Daily | ~5 MB | ~150 MB |
| **Total** | - | ~28 MB | **~432 MB/year** |

---

## 🎯 Success Metrics

1. **Coverage**: All 6 dataset groups loaded
2. **Freshness**: Data updated within 7 days of source update
3. **Reliability**: 95% successful weekly runs
4. **Quality**: Zero encoding errors in Keboola
5. **Monitoring**: Alerts on any failures

---

## 📝 Next Steps

1. **Immediate**:
   - Create extraction scripts
   - Test download of one dataset (DLP)
   - Inspect CSV structure

2. **This Week**:
   - Load all 5 core datasets to Keboola
   - Document table schemas

3. **Next Week**:
   - Add RZPRO integration
   - Create weekly update automation
   - Setup monitoring

---

## 📞 Resources

- **SÚKL Open Data**: https://opendata.sukl.cz/
- **Contact**: opendata@sukl.gov.cz
- **RZPRO Portal**: https://eregpublicsecure.ksrzis.cz/Registr/RZPRO/OpenData
- **Keboola Docs**: https://help.keboola.com/

---

**Last Updated**: October 15, 2025

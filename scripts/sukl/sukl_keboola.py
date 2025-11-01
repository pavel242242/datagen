"""
SÚKL AI Extractor - Keboola Custom Python Component Version
Uses Keboola CommonInterface to access user parameters
"""

import tempfile
import zipfile
import time
import re
from pathlib import Path
import requests
import anthropic
import pandas as pd
from keboola.component import CommonInterface

def log(msg):
    """Print with flush"""
    print(msg, flush=True)

# Initialize Keboola interface
ci = CommonInterface()

# Get user parameters - encrypted params (with #) are automatically decrypted in parameters
params = ci.configuration.parameters

# Debug: print what we have
log("="*70)
log("DEBUG: Configuration")
log(f"All params keys: {list(params.keys())}")
log("="*70)

# Encrypted parameters (with #) are automatically decrypted by Keboola
# Access directly from params
ANTHROPIC_API_KEY = params.get('#ANTHROPIC_API_KEY', '')

log(f"ANTHROPIC_API_KEY found: {bool(ANTHROPIC_API_KEY)}")
if not ANTHROPIC_API_KEY:
    log(f"ERROR: Available params: {list(params.keys())}")
    log(f"ERROR: Trying user_properties...")
    user_props = params.get('user_properties', {})
    log(f"user_properties: {list(user_props.keys())}")
    ANTHROPIC_API_KEY = user_props.get('#ANTHROPIC_API_KEY', '')
    log(f"Found in user_properties: {bool(ANTHROPIC_API_KEY)}")

DATASET_KEY = params.get('dataset', 'dlp')
BUCKET_ID = params.get('bucket_id', 'in.c-sukl')

log(f"Dataset parameter: {DATASET_KEY}")
log(f"Bucket: {BUCKET_ID}")

# No need to manually access Keboola credentials
# CommonInterface handles output tables automatically

# Dataset configurations
DATASETS = {
    'dlp': {
        'name': 'Medicines Database',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/databaze-lecivych-pripravku-dlp',
        'encoding': 'cp1250',
        'format': 'zip',
        'type': 'snapshot'  # Latest only
    },
    'dlp_history': {
        'name': 'DLP History',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/historie-databaze-lecivych-pripravku-dlp',
        'encoding': 'cp1250',
        'format': 'zip',
        'type': 'historical'  # All monthly files
    },
    'pharmacies': {
        'name': 'Pharmacy List',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/seznam-lekaren',
        'encoding': 'cp1250',
        'format': 'zip',
        'type': 'snapshot'  # Latest only
    },
    'lek13': {
        'name': 'LEK-13 Dispensing',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/lek-13',
        'encoding': 'cp1250',
        'format': 'zip',
        'type': 'historical'  # All monthly files
    },
    'dis13': {
        'name': 'DIS-13 Distribution',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/dis-13',
        'encoding': 'cp1250',
        'format': 'zip',
        'type': 'historical'  # All monthly files
    },
    'dis13_foreign': {
        'name': 'DIS-13 Foreign Distribution',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/dis-13-zahranici',
        'encoding': 'cp1250',
        'format': 'zip',
        'type': 'historical'  # All monthly files
    },
    'reg13': {
        'name': 'REG-13 Registration',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/reg-13',
        'encoding': 'cp1250',
        'format': 'zip',
        'type': 'historical'  # All monthly files
    },
    'rzpro': {
        'name': 'Medical Devices Registry',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/registr-zdravotnickych-prostredku',
        'encoding': 'cp1250',
        'format': 'zip',
        'type': 'snapshot'  # Latest only (daily updates)
    },
    'erecept': {
        'name': 'eRecept Prescriptions',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/predepsane-vydane-lecive-pripravky-ze-systemu-erecept',
        'encoding': 'utf-8',  # eRecept uses UTF-8
        'format': 'zip',
        'type': 'snapshot'  # Latest month only
    }
}

# log() already defined at top

def find_download_url(catalog_url, dataset_name, api_key):
    """Use Claude AI to find latest download URL"""
    log(f"🌐 Fetching: {catalog_url}")

    response = requests.get(catalog_url, timeout=30)
    html = response.text[:50000]  # Increased to 50KB to capture more links

    log("🤖 Using AI to find download link...")

    client = anthropic.Anthropic(api_key=api_key)

    # Retry logic for overloaded errors
    for attempt in range(3):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=300,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": f"""Find the DIRECT download URL for the LATEST {dataset_name} data file.

IMPORTANT:
- Look for links that point to actual FILES (ZIP or CSV)
- Links should end with .zip or .csv
- Find the most recent file (look for dates like "20250926" or "2025-09")
- Return ONLY the complete download URL starting with https://opendata.sukl.cz/
- DO NOT return catalog page URLs or info page URLs
- If multiple files exist, return the LATEST one

If not found, return: NOT_FOUND

HTML:
{html}"""
                }]
            )
            break
        except anthropic.OverloadedError:
            if attempt < 2:
                log(f"⏳ API overloaded, retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
            else:
                raise

    url = message.content[0].text.strip()

    if 'NOT_FOUND' in url or not url.startswith('http'):
        raise ValueError("Could not find download URL")

    log(f"✓ Found: {url}")
    return url

def find_all_download_urls(catalog_url, dataset_name, api_key):
    """Use Claude AI to find ALL historical download URLs"""
    log(f"🌐 Fetching: {catalog_url}")

    response = requests.get(catalog_url, timeout=30)
    html = response.text[:50000]

    log("🤖 Using AI to find ALL download links...")

    client = anthropic.Anthropic(api_key=api_key)

    # Retry logic for overloaded errors
    for attempt in range(3):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,  # More tokens for multiple URLs
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": f"""Find ALL DIRECT download URLs for {dataset_name} data files (all available months/years).

IMPORTANT:
- Look for links that point to actual FILES (ZIP or CSV)
- Links must end with .zip or .csv
- Find ALL files with dates in filenames (like "202001", "202002", etc.)
- Return one URL per line
- All URLs must start with https://opendata.sukl.cz/
- DO NOT include catalog page URLs or info page URLs
- Sort from oldest to newest if possible

If none found, return: NOT_FOUND

HTML:
{html}"""
                }]
            )
            break
        except anthropic.OverloadedError:
            if attempt < 2:
                log(f"⏳ API overloaded, retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
            else:
                raise

    response_text = message.content[0].text.strip()

    if 'NOT_FOUND' in response_text:
        raise ValueError("Could not find download URLs")

    # Parse URLs from response (one per line)
    urls = [line.strip() for line in response_text.split('\n')
            if line.strip().startswith('http')]

    if not urls:
        raise ValueError("Could not find download URLs")

    log(f"✓ Found {len(urls)} files")
    return urls

def download_file(url, dest_dir):
    """Download file"""
    filename = url.split('/')[-1]
    filepath = Path(dest_dir) / filename

    log(f"📥 Downloading: {url}")
    log(f"   Filename: {filename}")

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=65536):
            f.write(chunk)

    size_mb = filepath.stat().st_size / 1024 / 1024
    log(f"✓ Downloaded: {size_mb:.2f} MB")

    # Check file type
    with open(filepath, 'rb') as f:
        header = f.read(10)
        if header[:2] == b'PK':  # ZIP file magic bytes
            log(f"✓ File type: ZIP")
        elif header[:3] == b'\xef\xbb\xbf' or header[0:1].isalpha():  # CSV/text
            log(f"✓ File type: CSV/Text")
        else:
            log(f"⚠️ File type: Unknown (header: {header.hex()})")
            log(f"⚠️ This might be an HTML page instead of a data file")

    return filepath

def process_zip(zip_path, encoding, temp_dir, ci, bucket_id, prefix):
    """Extract ZIP and create output tables using CommonInterface"""
    log("📦 Extracting ZIP...")

    with zipfile.ZipFile(zip_path) as zf:
        csv_files = [f for f in zf.filelist if f.filename.endswith('.csv')]
        log(f"Found {len(csv_files)} CSV files")

        success = 0

        for file_info in csv_files:
            try:
                # Extract
                extracted = Path(temp_dir) / file_info.filename
                with zf.open(file_info) as source:
                    with open(extracted, 'wb') as target:
                        target.write(source.read())

                # Convert encoding to UTF-8
                df = pd.read_csv(extracted, encoding=encoding, sep=';', on_bad_lines='skip', low_memory=False)

                # Create output table name
                table_name = f"{prefix}_{file_info.filename.replace('.csv', '')}"
                destination = f"{bucket_id}.{table_name}"

                # Create output table definition
                out_table = ci.create_out_table_definition(
                    name=f"{table_name}.csv",
                    destination=destination,
                    incremental=False
                )

                # Write DataFrame to output table
                df.to_csv(out_table.full_path, index=False, encoding='utf-8')

                # Write manifest
                ci.write_manifest(out_table)

                log(f"  ✓ Created: {table_name} ({len(df):,} rows)")
                success += 1

            except Exception as e:
                log(f"  ⚠️ {file_info.filename}: {e}")

        log(f"✅ Processed {success}/{len(csv_files)} tables")

# Main execution
log("="*70)
log("🚀 SÚKL AI-Powered Data Extractor")
log("="*70)

# Validate
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not set in user parameters")

# Determine which datasets to process
if DATASET_KEY == 'all':
    log("\n🌍 Processing ALL datasets")
    datasets_to_process = list(DATASETS.keys())
elif DATASET_KEY == 'all_snapshot':
    log("\n📄 Processing all SNAPSHOT datasets")
    datasets_to_process = [k for k, v in DATASETS.items() if v.get('type') == 'snapshot']
elif DATASET_KEY == 'all_historical':
    log("\n📚 Processing all HISTORICAL datasets")
    datasets_to_process = [k for k, v in DATASETS.items() if v.get('type') == 'historical']
else:
    if DATASET_KEY not in DATASETS:
        raise ValueError(f"Unknown dataset: {DATASET_KEY}. Use 'all', 'all_snapshot', 'all_historical', or one of: {list(DATASETS.keys())}")
    datasets_to_process = [DATASET_KEY]

log(f"Will process {len(datasets_to_process)} dataset(s): {datasets_to_process}\n")

# Process each dataset
for dataset_idx, dataset_key in enumerate(datasets_to_process, 1):
    dataset = DATASETS[dataset_key]

    log("\n" + "="*70)
    log(f"🗂️  DATASET {dataset_idx}/{len(datasets_to_process)}: {dataset['name']}")
    log("="*70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Determine if we need all files or just latest
        dataset_type = dataset.get('type', 'snapshot')

        if dataset_type == 'historical':
            # Get ALL historical files
            log("📚 Fetching ALL historical files...")
            download_urls = find_all_download_urls(dataset['catalog'], dataset['name'], ANTHROPIC_API_KEY)
        else:
            # Get only the latest file
            log("📄 Fetching latest file...")
            download_urls = [find_download_url(dataset['catalog'], dataset['name'], ANTHROPIC_API_KEY)]

        log(f"\n🎯 Will process {len(download_urls)} file(s)\n")

        # Process each file
        for idx, download_url in enumerate(download_urls, 1):
            log(f"{'='*70}")
            log(f"📦 Processing file {idx}/{len(download_urls)}")
            log(f"{'='*70}")

            # Download
            filepath = download_file(download_url, tmpdir)

            # Extract month/date from filename for historical datasets
            # e.g., "lek13_202501.zip" -> "202501"
            filename = download_url.split('/')[-1]
            month_suffix = ''
            if dataset_type == 'historical':
                match = re.search(r'(\d{6})', filename)  # Find YYYYMM pattern
                if match:
                    month_suffix = f"_{match.group(1)}"

            # Process based on format
            try:
                if dataset['format'] == 'zip':
                    # Use suffix in table prefix for historical data
                    table_prefix = f"{dataset_key}{month_suffix}"
                    process_zip(filepath, dataset['encoding'], tmpdir, ci, BUCKET_ID, table_prefix)
                else:
                    log("⚠️ CSV processing not implemented")
            except zipfile.BadZipFile as e:
                log(f"❌ ERROR: File is not a valid ZIP file")
                log(f"   URL was: {download_url}")
                log(f"   This likely means Claude found the wrong link (catalog page instead of download)")
                raise ValueError(f"Invalid ZIP file from {download_url}. Claude may have found wrong URL.")

            log(f"✅ Completed file {idx}/{len(download_urls)}\n")

    log(f"✅ Completed dataset: {dataset['name']}\n")

log("\n" + "="*70)
log("✅ Extraction complete!")
log("="*70)

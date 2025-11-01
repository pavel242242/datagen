"""
SÚKL AI Extractor - For Keboola Custom Python Component
Paste this entire file into your Keboola Python extractor configuration
"""

import os
import tempfile
import zipfile
from pathlib import Path
import requests
import anthropic
import pandas as pd
from kbcstorage.client import Client

# ============================================================================
# CONFIGURATION - Set these in Keboola component configuration
# ============================================================================

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
KBC_TOKEN = os.environ.get('KBC_TOKEN', '')
KBC_URL = os.environ.get('KBC_URL', 'https://connection.us-east4.gcp.keboola.com/')
BUCKET_ID = 'in.c-sukl'

# Dataset to extract (change this to process different datasets)
DATASET_KEY = os.environ.get('DATASET', 'dlp')

# All available datasets
DATASETS = {
    'dlp': {
        'name': 'Medicines Database',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/databaze-lecivych-pripravku-dlp',
        'encoding': 'cp1250',
        'format': 'zip'
    },
    'pharmacies': {
        'name': 'Pharmacy List',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/seznam-lekaren',
        'encoding': 'cp1250',
        'format': 'zip'
    },
    'lek13': {
        'name': 'LEK-13 Dispensing',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/lek-13',
        'encoding': 'cp1250',
        'format': 'zip'
    },
    'dis13': {
        'name': 'DIS-13 Distribution',
        'catalog': 'https://opendata.sukl.cz/?q=katalog/dis-13',
        'encoding': 'cp1250',
        'format': 'csv'
    }
}

# ============================================================================
# MAIN EXTRACTION LOGIC
# ============================================================================

def log(msg):
    """Print with flush for Keboola logging"""
    print(msg, flush=True)

def find_download_url(catalog_url, dataset_name, api_key):
    """Use Claude AI to find latest download URL"""
    log(f"🌐 Fetching catalog: {catalog_url}")

    response = requests.get(catalog_url, timeout=30)
    html = response.text[:15000]  # First 15KB

    log("🤖 Using AI to find download link...")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=300,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""Find the direct download URL for the LATEST {dataset_name} file.

Instructions:
- Look for download links (ZIP or CSV)
- Find most recent file (check dates like "20250926" or "202509")
- Return ONLY the full URL starting with https://opendata.sukl.cz/
- If not found, return: NOT_FOUND

HTML:
{html}"""
        }]
    )

    url = message.content[0].text.strip()

    if 'NOT_FOUND' in url or not url.startswith('http'):
        raise ValueError("Could not find download URL")

    log(f"✓ Found: {url}")
    return url

def download_file(url, dest_dir):
    """Download file to destination directory"""
    filename = url.split('/')[-1]
    filepath = Path(dest_dir) / filename

    log(f"📥 Downloading {filename}...")

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=65536):
            f.write(chunk)

    size_mb = filepath.stat().st_size / 1024 / 1024
    log(f"✓ Downloaded: {size_mb:.2f} MB")

    return filepath

def process_zip(zip_path, encoding, temp_dir, kbc, bucket_id, prefix):
    """Extract ZIP and upload CSVs to Keboola"""
    log("📦 Extracting ZIP...")

    with zipfile.ZipFile(zip_path) as zf:
        csv_files = [f for f in zf.filelist if f.filename.endswith('.csv')]
        log(f"Found {len(csv_files)} CSV files")

        # Ensure bucket exists
        try:
            kbc.buckets.detail(bucket_id)
        except:
            bucket_name = bucket_id.split('.')[-1].replace('c-', '')
            kbc.buckets.create(name=bucket_name, stage='in', description='SÚKL Open Data')
            log(f"✓ Created bucket: {bucket_id}")

        success = 0

        for file_info in csv_files:
            try:
                # Extract
                extracted = Path(temp_dir) / file_info.filename
                with zf.open(file_info) as source:
                    with open(extracted, 'wb') as target:
                        target.write(source.read())

                # Convert encoding and delimiter
                df = pd.read_csv(
                    extracted,
                    encoding=encoding,
                    sep=';',
                    on_bad_lines='skip',
                    low_memory=False
                )

                # Save as UTF-8 CSV
                converted = Path(temp_dir) / f"conv_{file_info.filename}"
                df.to_csv(converted, index=False, encoding='utf-8')

                # Upload to Keboola
                table_name = f"{prefix}_{file_info.filename.replace('.csv', '')}"
                full_table_id = f"{bucket_id}.{table_name}"

                try:
                    kbc.tables.detail(full_table_id)
                    kbc.tables.load(
                        table_id=full_table_id,
                        file_path=str(converted),
                        is_incremental=False
                    )
                    log(f"  ✓ Updated: {table_name} ({len(df):,} rows)")
                except:
                    kbc.tables.create(
                        name=table_name,
                        bucket_id=bucket_id,
                        file_path=str(converted)
                    )
                    log(f"  ✓ Created: {table_name} ({len(df):,} rows)")

                success += 1

            except Exception as e:
                log(f"  ⚠️ {file_info.filename}: {e}")

        log(f"✅ Uploaded {success}/{len(csv_files)} tables")

def main():
    """Main extraction process"""
    log("="*70)
    log("🚀 SÚKL AI-Powered Data Extractor")
    log("="*70)

    # Validate credentials
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")
    if not KBC_TOKEN:
        raise ValueError("KBC_TOKEN not set")

    # Get dataset config
    if DATASET_KEY not in DATASETS:
        raise ValueError(f"Unknown dataset: {DATASET_KEY}")

    dataset = DATASETS[DATASET_KEY]

    log(f"\nDataset: {dataset['name']}")
    log(f"Bucket: {BUCKET_ID}")
    log("")

    # Initialize Keboola client
    kbc = Client(KBC_URL, KBC_TOKEN)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Find download URL using AI
        download_url = find_download_url(
            dataset['catalog'],
            dataset['name'],
            ANTHROPIC_API_KEY
        )

        # Step 2: Download file
        filepath = download_file(download_url, tmpdir)

        # Step 3: Process and upload
        if dataset['format'] == 'zip':
            process_zip(
                filepath,
                dataset['encoding'],
                tmpdir,
                kbc,
                BUCKET_ID,
                DATASET_KEY
            )
        else:
            # Direct CSV (not implemented yet)
            log("⚠️ Direct CSV processing not implemented")

    log("\n" + "="*70)
    log("✅ Extraction complete!")
    log("="*70)

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    main()

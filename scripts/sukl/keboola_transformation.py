#!/usr/bin/env python3
"""
SÚKL AI Extractor - Keboola Transformation
Runs as a Python transformation in Keboola Connection
"""

import os
import json
import tempfile
import zipfile
from pathlib import Path
import requests
import anthropic
import pandas as pd
from kbcstorage.client import Client


# Configuration - will be set via Keboola parameters
DATASETS = {
    "dlp": {
        "name": "Medicines Database (DLP)",
        "catalog_url": "https://opendata.sukl.cz/?q=katalog/databaze-lecivych-pripravku-dlp",
        "encoding": "cp1250",
        "format": "zip",
        "prefix": "dlp"
    },
    "pharmacies": {
        "name": "Pharmacy List",
        "catalog_url": "https://opendata.sukl.cz/?q=katalog/seznam-lekaren",
        "encoding": "cp1250",
        "format": "zip",
        "prefix": "pharmacies"
    },
    "lek13": {
        "name": "LEK-13 Dispensing",
        "catalog_url": "https://opendata.sukl.cz/?q=katalog/lek-13",
        "encoding": "cp1250",
        "format": "zip",
        "prefix": "lek13"
    },
    "dis13": {
        "name": "DIS-13 Distribution",
        "catalog_url": "https://opendata.sukl.cz/?q=katalog/dis-13",
        "encoding": "cp1250",
        "format": "csv",
        "prefix": "dis13"
    },
    "erecept": {
        "name": "eRecept Data",
        "catalog_url": "https://opendata.sukl.cz/?q=katalog/predepsane-vydane-lecive-pripravky-ze-systemu-erecept",
        "encoding": "utf-8",
        "format": "zip",
        "prefix": "erecept"
    }
}


def log(message):
    """Print with flush for Keboola logging"""
    print(message, flush=True)


def get_download_url_with_ai(catalog_url: str, dataset_name: str, api_key: str) -> str:
    """Use Claude to find download URL from catalog page"""
    log(f"🌐 Fetching catalog: {catalog_url}")

    response = requests.get(catalog_url, timeout=30)
    response.raise_for_status()
    html = response.text[:15000]  # Limit to save tokens

    log(f"🤖 Using AI to find download link...")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""You are analyzing a Czech open data catalog page from SÚKL.

Dataset: {dataset_name}

Task: Find the direct download URL for the LATEST version of this dataset.

Look for:
- Download links (ZIP or CSV files)
- Most recent file (check dates in filenames)
- Full URLs starting with https://opendata.sukl.cz/

Return ONLY the download URL, nothing else. If not found, return "NOT_FOUND".

HTML:
{html}"""
        }]
    )

    url = message.content[0].text.strip()

    if url == "NOT_FOUND" or not url.startswith("http"):
        raise ValueError(f"AI could not find download URL for {dataset_name}")

    log(f"   ✓ Found: {url}")
    return url


def download_file(url: str, dest_path: Path):
    """Download file with progress"""
    log(f"📥 Downloading {url.split('/')[-1]}...")

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0 and downloaded % (1024 * 1024) == 0:  # Log every MB
                log(f"   Downloaded: {downloaded / 1024 / 1024:.1f} MB")

    log(f"   ✓ Complete: {dest_path.stat().st_size / 1024 / 1024:.2f} MB")


def process_zip(zip_path: Path, encoding: str, temp_dir: Path):
    """Extract ZIP and convert CSVs"""
    log(f"📦 Extracting ZIP...")

    csv_files = []

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.filelist:
            if not info.filename.endswith('.csv'):
                continue

            # Extract
            extracted = temp_dir / info.filename
            with zf.open(info) as source, open(extracted, 'wb') as target:
                target.write(source.read())

            # Convert
            try:
                df = pd.read_csv(extracted, encoding=encoding, sep=';', on_bad_lines='skip')

                # Write as UTF-8 CSV
                output = temp_dir / f"converted_{info.filename}"
                df.to_csv(output, index=False, encoding='utf-8')

                csv_files.append({
                    'path': output,
                    'name': info.filename.replace('.csv', ''),
                    'rows': len(df)
                })

                log(f"   ✓ {info.filename}: {len(df):,} rows")
            except Exception as e:
                log(f"   ⚠️  {info.filename}: {e}")

    return csv_files


def upload_to_keboola(csv_files: list, prefix: str, kbc: Client, bucket_id: str):
    """Upload CSVs to Keboola"""
    log(f"☁️  Uploading {len(csv_files)} tables to {bucket_id}...")

    # Ensure bucket exists
    try:
        kbc.buckets.detail(bucket_id)
    except:
        bucket_name = bucket_id.split('.')[-1].replace('c-', '')
        kbc.buckets.create(name=bucket_name, stage='in', description='SÚKL Open Data')
        log(f"   ✓ Created bucket: {bucket_id}")

    success = 0
    for csv_file in csv_files:
        table_name = f"{prefix}_{csv_file['name']}"
        full_table_id = f"{bucket_id}.{table_name}"

        try:
            # Create or update table
            try:
                kbc.tables.detail(full_table_id)
                kbc.tables.load(table_id=full_table_id, file_path=str(csv_file['path']), is_incremental=False)
                log(f"   ✓ Updated: {table_name} ({csv_file['rows']:,} rows)")
            except:
                kbc.tables.create(name=table_name, bucket_id=bucket_id, file_path=str(csv_file['path']))
                log(f"   ✓ Created: {table_name} ({csv_file['rows']:,} rows)")

            success += 1
        except Exception as e:
            log(f"   ✗ {table_name}: {e}")

    log(f"✅ Uploaded {success}/{len(csv_files)} tables")


def main():
    """Main extraction process"""
    log("\n" + "="*70)
    log("🚀 SÚKL AI-Powered Data Extraction")
    log("="*70 + "\n")

    # Get credentials from environment
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    keboola_url = os.getenv('KBC_URL')
    keboola_token = os.getenv('KBC_TOKEN')
    bucket_id = os.getenv('BUCKET_ID', 'in.c-sukl')

    if not all([anthropic_key, keboola_url, keboola_token]):
        raise ValueError("Missing required credentials: ANTHROPIC_API_KEY, KBC_URL, KBC_TOKEN")

    # Initialize Keboola client
    kbc = Client(keboola_url, keboola_token)

    # Get dataset list (default to all, or from environment)
    dataset_keys = os.getenv('DATASETS', 'dlp,pharmacies,lek13,dis13,erecept').split(',')

    log(f"Processing {len(dataset_keys)} datasets: {', '.join(dataset_keys)}\n")

    # Process each dataset
    for dataset_key in dataset_keys:
        if dataset_key not in DATASETS:
            log(f"⚠️  Unknown dataset: {dataset_key}, skipping")
            continue

        dataset = DATASETS[dataset_key]

        log("\n" + "="*70)
        log(f"Processing: {dataset['name']}")
        log("="*70)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Step 1: AI finds download URL
                download_url = get_download_url_with_ai(
                    dataset['catalog_url'],
                    dataset['name'],
                    anthropic_key
                )

                # Step 2: Download file
                filename = download_url.split('/')[-1]
                file_path = temp_path / filename
                download_file(download_url, file_path)

                # Step 3: Process based on format
                if dataset['format'] == 'zip':
                    csv_files = process_zip(file_path, dataset['encoding'], temp_path)
                else:
                    # Direct CSV
                    log("📝 Converting CSV...")
                    df = pd.read_csv(file_path, encoding=dataset['encoding'], sep=';', on_bad_lines='skip')
                    output = temp_path / "converted.csv"
                    df.to_csv(output, index=False, encoding='utf-8')
                    csv_files = [{'path': output, 'name': dataset_key, 'rows': len(df)}]
                    log(f"   ✓ Converted: {len(df):,} rows")

                # Step 4: Upload to Keboola
                if csv_files:
                    upload_to_keboola(csv_files, dataset['prefix'], kbc, bucket_id)

            log(f"\n✅ Completed: {dataset['name']}")

        except Exception as e:
            log(f"\n❌ Error: {e}")
            continue

    log("\n" + "="*70)
    log("🎉 Extraction complete!")
    log("="*70)


if __name__ == '__main__':
    main()

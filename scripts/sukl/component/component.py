#!/usr/bin/env python3
"""
Keboola SÚKL Extractor Component
AI-powered extraction of Czech pharmaceutical open data
"""

import os
import sys
import json
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

import requests
import anthropic
import pandas as pd
from kbcstorage.client import Client


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class SUKLExtractor:
    """SÚKL Open Data Extractor with AI-powered URL discovery"""

    DATASETS = {
        "dlp": {
            "name": "Medicines Database (DLP)",
            "catalog_url": "https://opendata.sukl.cz/?q=katalog/databaze-lecivych-pripravku-dlp",
            "encoding": "cp1250",
            "format": "zip",
            "description": "Complete database of registered medicines in Czech Republic"
        },
        "pharmacies": {
            "name": "Pharmacy List",
            "catalog_url": "https://opendata.sukl.cz/?q=katalog/seznam-lekaren",
            "encoding": "cp1250",
            "format": "zip",
            "description": "List of all licensed pharmacies"
        },
        "lek13": {
            "name": "LEK-13 Dispensing Reports",
            "catalog_url": "https://opendata.sukl.cz/?q=katalog/lek-13",
            "encoding": "cp1250",
            "format": "zip",
            "description": "Monthly pharmacy dispensing statistics"
        },
        "dis13": {
            "name": "DIS-13 Distribution Reports",
            "catalog_url": "https://opendata.sukl.cz/?q=katalog/dis-13",
            "encoding": "cp1250",
            "format": "csv",
            "description": "Monthly distribution reports from authorized distributors"
        },
        "erecept": {
            "name": "eRecept Prescription Data",
            "catalog_url": "https://opendata.sukl.cz/?q=katalog/predepsane-vydane-lecive-pripravky-ze-systemu-erecept",
            "encoding": "utf-8",
            "format": "zip",
            "description": "Electronic prescription and dispensation data"
        }
    }

    def __init__(self, data_dir: Path, config: Dict):
        """Initialize extractor with configuration"""
        self.data_dir = data_dir
        self.config = config
        self.temp_dir = Path(tempfile.mkdtemp())

        # Get parameters
        params = config.get('parameters', {})
        self.datasets_to_process = params.get('datasets', ['dlp'])
        self.bucket_id = params.get('bucket_id', 'in.c-sukl')

        # Get credentials from config (encrypted by Keboola)
        self.anthropic_key = config.get('#anthropic_api_key')
        kbc_token = config.get('#kbc_token')
        kbc_url = os.getenv('KBC_URL', 'https://connection.keboola.com')

        if not self.anthropic_key:
            raise ValueError("Anthropic API key not configured")

        if not kbc_token:
            raise ValueError("Keboola token not configured")

        # Initialize clients
        self.anthropic = anthropic.Anthropic(api_key=self.anthropic_key)
        self.kbc = Client(kbc_url, kbc_token)

        logger.info(f"Initialized SÚKL Extractor")
        logger.info(f"Bucket: {self.bucket_id}")
        logger.info(f"Datasets: {', '.join(self.datasets_to_process)}")

    def fetch_catalog_page(self, url: str) -> str:
        """Fetch HTML from catalog page"""
        logger.info(f"Fetching catalog: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def find_download_url_with_ai(self, catalog_url: str, dataset_name: str) -> str:
        """Use Claude AI to extract download URL from catalog page"""
        logger.info(f"Using AI to find download link for: {dataset_name}")

        html = self.fetch_catalog_page(catalog_url)

        # Limit HTML to save tokens (first 15KB usually contains the download link)
        html_snippet = html[:15000]

        prompt = f"""You are analyzing a Czech government open data catalog page from SÚKL (State Institute for Drug Control).

Dataset: {dataset_name}

Task: Find the direct download URL for the LATEST/CURRENT version of this dataset.

Instructions:
1. Look for download links (typically ZIP or CSV files)
2. Find the most recent file (check dates in URLs like "20250926" or "202509")
3. Return the COMPLETE URL starting with https://opendata.sukl.cz/
4. If multiple files exist, choose the one with the latest date
5. Return ONLY the URL, nothing else

If you cannot find a download URL, return exactly: NOT_FOUND

HTML content:
{html_snippet}"""

        try:
            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            url = message.content[0].text.strip()

            if url == "NOT_FOUND" or not url.startswith("http"):
                raise ValueError(f"AI could not find download URL")

            logger.info(f"Found URL: {url}")
            return url

        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            raise

    def download_file(self, url: str) -> Path:
        """Download file to temp directory"""
        filename = url.split('/')[-1]
        filepath = self.temp_dir / filename

        logger.info(f"Downloading: {filename}")

        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)

        size_mb = filepath.stat().st_size / 1024 / 1024
        logger.info(f"Downloaded: {size_mb:.2f} MB")

        return filepath

    def extract_and_convert_zip(self, zip_path: Path, encoding: str) -> List[Path]:
        """Extract ZIP and convert CSVs to UTF-8"""
        logger.info("Extracting and converting CSVs...")

        converted_files = []

        with zipfile.ZipFile(zip_path, 'r') as zf:
            csv_files = [f for f in zf.filelist if f.filename.endswith('.csv')]
            logger.info(f"Found {len(csv_files)} CSV files in ZIP")

            for file_info in csv_files:
                try:
                    # Extract to temp
                    extracted_path = self.temp_dir / file_info.filename
                    with zf.open(file_info) as source:
                        with open(extracted_path, 'wb') as target:
                            target.write(source.read())

                    # Read with original encoding and semicolon delimiter
                    df = pd.read_csv(
                        extracted_path,
                        encoding=encoding,
                        sep=';',
                        on_bad_lines='skip',
                        low_memory=False
                    )

                    # Save as UTF-8 with comma delimiter
                    output_path = self.temp_dir / f"converted_{file_info.filename}"
                    df.to_csv(output_path, index=False, encoding='utf-8')

                    converted_files.append(output_path)
                    logger.info(f"  ✓ {file_info.filename}: {len(df):,} rows, {len(df.columns)} columns")

                except Exception as e:
                    logger.warning(f"  ⚠ {file_info.filename}: {e}")

        return converted_files

    def convert_csv(self, csv_path: Path, encoding: str) -> Path:
        """Convert single CSV file"""
        logger.info("Converting CSV...")

        df = pd.read_csv(
            csv_path,
            encoding=encoding,
            sep=';',
            on_bad_lines='skip',
            low_memory=False
        )

        output_path = self.temp_dir / f"converted_{csv_path.name}"
        df.to_csv(output_path, index=False, encoding='utf-8')

        logger.info(f"Converted: {len(df):,} rows, {len(df.columns)} columns")
        return output_path

    def upload_to_keboola(self, csv_files: List[Path], prefix: str):
        """Upload CSV files to Keboola Storage"""
        logger.info(f"Uploading {len(csv_files)} tables to {self.bucket_id}...")

        # Ensure bucket exists
        try:
            self.kbc.buckets.detail(self.bucket_id)
            logger.info("Bucket exists")
        except:
            bucket_name = self.bucket_id.split('.')[-1].replace('c-', '')
            self.kbc.buckets.create(
                name=bucket_name,
                stage='in',
                description='SÚKL Open Data - Czech pharmaceutical data'
            )
            logger.info(f"Created bucket: {self.bucket_id}")

        success_count = 0

        for csv_file in csv_files:
            # Generate table name from filename
            base_name = csv_file.name.replace('converted_', '').replace('.csv', '')
            table_name = f"{prefix}_{base_name}"
            full_table_id = f"{self.bucket_id}.{table_name}"

            try:
                # Check if table exists
                try:
                    self.kbc.tables.detail(full_table_id)
                    # Update existing table
                    self.kbc.tables.load(
                        table_id=full_table_id,
                        file_path=str(csv_file),
                        is_incremental=False
                    )
                    logger.info(f"  ✓ Updated: {table_name}")
                except:
                    # Create new table
                    self.kbc.tables.create(
                        name=table_name,
                        bucket_id=self.bucket_id,
                        file_path=str(csv_file)
                    )
                    logger.info(f"  ✓ Created: {table_name}")

                success_count += 1

            except Exception as e:
                logger.error(f"  ✗ {table_name}: {e}")

        logger.info(f"Successfully uploaded {success_count}/{len(csv_files)} tables")

    def process_dataset(self, dataset_key: str):
        """Process a single dataset end-to-end"""
        if dataset_key not in self.DATASETS:
            logger.error(f"Unknown dataset: {dataset_key}")
            return

        dataset = self.DATASETS[dataset_key]

        logger.info("="*70)
        logger.info(f"Processing: {dataset['name']}")
        logger.info(f"Description: {dataset['description']}")
        logger.info("="*70)

        try:
            # Step 1: Find download URL using AI
            download_url = self.find_download_url_with_ai(
                dataset['catalog_url'],
                dataset['name']
            )

            # Step 2: Download file
            file_path = self.download_file(download_url)

            # Step 3: Extract/convert based on format
            if dataset['format'] == 'zip':
                csv_files = self.extract_and_convert_zip(file_path, dataset['encoding'])
            else:
                csv_files = [self.convert_csv(file_path, dataset['encoding'])]

            # Step 4: Upload to Keboola
            if csv_files:
                self.upload_to_keboola(csv_files, dataset_key)
                logger.info(f"✅ Successfully processed {dataset['name']}")
            else:
                logger.warning("No CSV files to upload")

        except Exception as e:
            logger.error(f"❌ Failed to process {dataset['name']}: {e}")
            raise

    def run(self):
        """Run extraction for all configured datasets"""
        logger.info("\n" + "="*70)
        logger.info("🚀 SÚKL AI-Powered Data Extractor")
        logger.info("="*70 + "\n")

        for dataset_key in self.datasets_to_process:
            try:
                self.process_dataset(dataset_key)
            except Exception as e:
                logger.error(f"Dataset {dataset_key} failed: {e}")
                # Continue with next dataset
                continue

        logger.info("\n" + "="*70)
        logger.info("🎉 Extraction complete!")
        logger.info("="*70)

        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    """Component entry point"""
    # Keboola provides config in /data/config.json
    data_dir = Path(os.getenv('KBC_DATADIR', '/data/'))
    config_file = data_dir / 'config.json'

    if not config_file.exists():
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)

    with open(config_file, 'r') as f:
        config = json.load(f)

    extractor = SUKLExtractor(data_dir, config)
    extractor.run()


if __name__ == '__main__':
    main()

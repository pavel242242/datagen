#!/usr/bin/env python3
"""
AI-Powered SÚKL Data Extractor
Uses Claude AI to intelligently scrape catalog pages and find download links
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional, List
import anthropic
import pandas as pd
from kbcstorage.client import Client


class AIExtractor:
    def __init__(self, config_path: str = "ai_config.json"):
        """Initialize AI extractor"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # Initialize Claude client
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")

        self.claude = anthropic.Anthropic(api_key=anthropic_key)

        # Initialize Keboola client
        keboola_url = os.getenv('KEBOOLA_URL')
        keboola_token = os.getenv('KEBOOLA_TOKEN')

        if not keboola_url or not keboola_token:
            raise ValueError("KEBOOLA_URL and KEBOOLA_TOKEN must be set")

        self.keboola = Client(keboola_url, keboola_token)
        self.bucket_id = self.config['keboola']['bucket']

        # Setup directories
        self.download_dir = Path(self.config['download_dir'])
        self.output_dir = Path(self.config['output_dir'])
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch_catalog_page(self, url: str) -> str:
        """Fetch HTML content from catalog page"""
        print(f"🌐 Fetching catalog: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def extract_download_url_with_ai(self, html_content: str, dataset_name: str) -> Optional[str]:
        """Use Claude to extract download URL from HTML"""
        print(f"🤖 Using AI to find download link for: {dataset_name}")

        prompt = f"""You are analyzing a Czech open data catalog page from SÚKL (State Institute for Drug Control).

Dataset: {dataset_name}

Task: Find the direct download URL for the LATEST version of this dataset.

Look for:
- Download links (usually ZIP or CSV files)
- The most recent file (check dates in filenames or on page)
- Full URLs starting with https://opendata.sukl.cz/

Return ONLY the download URL, nothing else. If you cannot find it, return "NOT_FOUND".

HTML content:
{html_content[:15000]}
"""

        try:
            message = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            url = message.content[0].text.strip()

            if url == "NOT_FOUND" or not url.startswith("http"):
                print(f"   ⚠️  AI could not find download URL")
                return None

            print(f"   ✓ Found: {url}")
            return url

        except Exception as e:
            print(f"   ✗ AI Error: {e}")
            return None

    def download_file(self, url: str, filename: str) -> Path:
        """Download file with progress"""
        filepath = self.download_dir / filename

        print(f"📥 Downloading {filename}...")
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r   Progress: {percent:.1f}%", end='', flush=True)

        print(f"\n   ✓ Downloaded {filepath.stat().st_size / 1024 / 1024:.2f} MB")
        return filepath

    def extract_and_convert(self, zip_path: Path, dataset_key: str) -> List[Path]:
        """Extract ZIP and convert CSVs to UTF-8"""
        import zipfile

        dataset = self.config['datasets'][dataset_key]
        extract_dir = self.output_dir / dataset_key
        extract_dir.mkdir(parents=True, exist_ok=True)

        print(f"📦 Extracting and converting...")

        converted_files = []

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                if not file_info.filename.endswith('.csv'):
                    continue

                # Extract
                zip_ref.extract(file_info, extract_dir)
                extracted_path = extract_dir / file_info.filename

                # Convert encoding and delimiter
                output_path = extract_dir / f"converted_{file_info.filename}"

                try:
                    df = pd.read_csv(
                        extracted_path,
                        encoding=dataset['encoding'],
                        sep=';',
                        on_bad_lines='skip'
                    )
                    df.to_csv(output_path, index=False, encoding='utf-8')

                    print(f"   ✓ {file_info.filename}: {len(df):,} rows")
                    converted_files.append(output_path)
                except Exception as e:
                    print(f"   ⚠️  {file_info.filename}: {e}")

        return converted_files

    def upload_to_keboola(self, csv_files: List[Path], dataset_key: str):
        """Upload converted CSVs to Keboola"""
        dataset = self.config['datasets'][dataset_key]
        prefix = dataset['keboola_prefix']

        print(f"☁️  Uploading to Keboola bucket: {self.bucket_id}")

        # Ensure bucket exists
        try:
            self.keboola.buckets.detail(self.bucket_id)
        except Exception:
            bucket_name = self.bucket_id.split('.')[-1].replace('c-', '')
            self.keboola.buckets.create(
                name=bucket_name,
                stage='in',
                description='SÚKL Open Data (AI-extracted)'
            )

        success_count = 0
        for csv_file in csv_files:
            # Remove 'converted_' prefix from filename
            clean_name = csv_file.name.replace('converted_', '').replace('.csv', '')
            table_name = f"{prefix}_{clean_name}"
            full_table_id = f"{self.bucket_id}.{table_name}"

            try:
                # Check if table exists
                try:
                    self.keboola.tables.detail(full_table_id)
                    self.keboola.tables.load(
                        table_id=full_table_id,
                        file_path=str(csv_file),
                        is_incremental=False
                    )
                    print(f"   ✓ Updated: {table_name}")
                except Exception:
                    self.keboola.tables.create(
                        name=table_name,
                        bucket_id=self.bucket_id,
                        file_path=str(csv_file)
                    )
                    print(f"   ✓ Created: {table_name}")

                success_count += 1
            except Exception as e:
                print(f"   ✗ {table_name}: {e}")

        print(f"\n✅ Uploaded {success_count}/{len(csv_files)} tables")

    def process_dataset(self, dataset_key: str):
        """Process a single dataset end-to-end"""
        dataset = self.config['datasets'][dataset_key]

        print("=" * 70)
        print(f"Processing: {dataset['name']}")
        print("=" * 70)

        # Step 1: Fetch catalog page
        html = self.fetch_catalog_page(dataset['catalog_url'])

        # Step 2: Use AI to find download URL
        download_url = self.extract_download_url_with_ai(html, dataset['name'])

        if not download_url:
            print("❌ Could not find download URL. Skipping.")
            return

        # Step 3: Download file
        filename = download_url.split('/')[-1]
        filepath = self.download_file(download_url, filename)

        # Step 4: Extract and convert (only for ZIP files)
        if dataset['format'] == 'zip':
            converted_files = self.extract_and_convert(filepath, dataset_key)

            # Step 5: Upload to Keboola
            if converted_files:
                self.upload_to_keboola(converted_files, dataset_key)
        else:
            # Direct CSV file
            print("📝 Direct CSV file - converting...")
            output_path = self.output_dir / f"converted_{filename}"

            try:
                df = pd.read_csv(filepath, encoding=dataset['encoding'], sep=';', on_bad_lines='skip')
                df.to_csv(output_path, index=False, encoding='utf-8')
                print(f"   ✓ Converted: {len(df):,} rows")

                self.upload_to_keboola([output_path], dataset_key)
            except Exception as e:
                print(f"   ✗ Error: {e}")

        print("\n" + "=" * 70)
        print(f"✅ Completed: {dataset['name']}")
        print("=" * 70 + "\n")

    def process_all(self):
        """Process all configured datasets"""
        print("\n🚀 AI-Powered SÚKL Data Extraction")
        print(f"Datasets: {len(self.config['datasets'])}")
        print("=" * 70 + "\n")

        for dataset_key in self.config['datasets'].keys():
            try:
                self.process_dataset(dataset_key)
                time.sleep(2)  # Be polite to the server
            except Exception as e:
                print(f"❌ Error processing {dataset_key}: {e}\n")
                continue

        print("\n🎉 All datasets processed!")


def main():
    """Main entry point"""
    import sys

    extractor = AIExtractor()

    if len(sys.argv) > 1:
        # Process specific dataset
        dataset_key = sys.argv[1]
        extractor.process_dataset(dataset_key)
    else:
        # Process all datasets
        extractor.process_all()


if __name__ == '__main__':
    main()

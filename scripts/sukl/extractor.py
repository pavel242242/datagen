#!/usr/bin/env python3
"""
SÚKL Data Extractor
Downloads and extracts datasets from opendata.sukl.cz
"""

import os
import json
import zipfile
import requests
from pathlib import Path
from typing import Dict, List


class SUKLExtractor:
    def __init__(self, config_path: str = "config.json"):
        """Initialize extractor with configuration"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.download_dir = Path(self.config['download_dir'])
        self.output_dir = Path(self.config['output_dir'])

        # Create directories if they don't exist
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_dataset(self, dataset_key: str) -> Path:
        """Download a dataset by key"""
        dataset = self.config['datasets'][dataset_key]
        url = dataset['url']
        filename = url.split('/')[-1]
        filepath = self.download_dir / filename

        print(f"📥 Downloading {dataset['name']}...")
        print(f"   URL: {url}")

        response = requests.get(url, stream=True)
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

        print(f"\n   ✓ Downloaded to {filepath}")
        print(f"   Size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")

        return filepath

    def extract_zip(self, zip_path: Path, dataset_key: str) -> List[Path]:
        """Extract ZIP file and return list of CSV files"""
        dataset = self.config['datasets'][dataset_key]
        extract_dir = self.output_dir / dataset_key
        extract_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📦 Extracting {zip_path.name}...")

        csv_files = []
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                print(f"   - {file_info.filename} ({file_info.file_size / 1024:.1f} KB)")
                zip_ref.extract(file_info, extract_dir)

                extracted_path = extract_dir / file_info.filename
                if extracted_path.suffix.lower() == '.csv':
                    csv_files.append(extracted_path)

        print(f"   ✓ Extracted {len(csv_files)} CSV files")
        return csv_files

    def inspect_csv(self, csv_path: Path, encoding: str = 'cp1250', max_rows: int = 5):
        """Inspect CSV file structure"""
        import pandas as pd

        print(f"\n🔍 Inspecting {csv_path.name}...")

        try:
            df = pd.read_csv(csv_path, encoding=encoding, nrows=max_rows)

            print(f"   Shape: {df.shape[0]} rows x {df.shape[1]} columns (showing first {max_rows})")
            print(f"   Columns: {list(df.columns)}")
            print(f"\n   Sample data:")
            print(df.to_string(index=False))

            return {
                'filename': csv_path.name,
                'columns': list(df.columns),
                'row_count': len(df),
                'encoding': encoding
            }
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            return None

    def process_dataset(self, dataset_key: str):
        """Download, extract, and inspect a dataset"""
        dataset = self.config['datasets'][dataset_key]

        print("=" * 60)
        print(f"Processing: {dataset['name']}")
        print("=" * 60)

        # Download
        filepath = self.download_dataset(dataset_key)

        # Extract if ZIP
        if dataset['format'] == 'zip':
            csv_files = self.extract_zip(filepath, dataset_key)

            # Inspect each CSV
            results = []
            for csv_file in csv_files:
                result = self.inspect_csv(csv_file, dataset['encoding'])
                if result:
                    results.append(result)

            return results
        else:
            # Direct CSV file
            result = self.inspect_csv(filepath, dataset['encoding'])
            return [result] if result else []


def main():
    """Main entry point"""
    import sys

    extractor = SUKLExtractor()

    if len(sys.argv) > 1:
        dataset_key = sys.argv[1]
    else:
        dataset_key = 'dlp'  # Default to DLP

    print(f"\n🚀 SÚKL Data Extractor")
    print(f"Dataset: {dataset_key}\n")

    results = extractor.process_dataset(dataset_key)

    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print(f"Found {len(results)} CSV files")
    print("=" * 60)


if __name__ == '__main__':
    main()

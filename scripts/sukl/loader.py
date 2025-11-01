#!/usr/bin/env python3
"""
SÚKL Data Loader
Converts and uploads SÚKL datasets to Keboola Connection
"""

import os
import json
import csv
from pathlib import Path
from typing import List
from kbcstorage.client import Client
import pandas as pd


class SUKLLoader:
    def __init__(self, config_path: str = "config.json"):
        """Initialize loader with configuration"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # Get Keboola credentials from environment
        keboola_url = os.getenv('KEBOOLA_URL')
        keboola_token = os.getenv('KEBOOLA_TOKEN')

        if not keboola_url or not keboola_token:
            raise ValueError("KEBOOLA_URL and KEBOOLA_TOKEN must be set")

        self.client = Client(keboola_url, keboola_token)
        self.bucket_id = self.config['keboola']['bucket']
        self.output_dir = Path(self.config['output_dir'])

    def ensure_bucket(self):
        """Ensure Keboola bucket exists"""
        print(f"📦 Checking bucket: {self.bucket_id}")

        try:
            self.client.buckets.detail(self.bucket_id)
            print(f"   ✓ Bucket exists")
        except Exception:
            print(f"   Creating bucket...")
            # Extract bucket name from ID (e.g., 'in.c-sukl' -> 'sukl')
            bucket_name = self.bucket_id.split('.')[-1].replace('c-', '')
            self.client.buckets.create(
                name=bucket_name,
                stage='in',
                description='SÚKL Open Data (State Institute for Drug Control)'
            )
            print(f"   ✓ Created bucket: {self.bucket_id}")

    def convert_csv(self, input_path: Path, output_path: Path, encoding: str = 'cp1250'):
        """Convert CSV to UTF-8 with proper delimiter"""
        print(f"   Converting {input_path.name}...")

        try:
            # Read with semicolon delimiter and original encoding
            df = pd.read_csv(input_path, encoding=encoding, sep=';', on_bad_lines='skip')

            # Write as UTF-8 CSV with comma delimiter
            df.to_csv(output_path, index=False, encoding='utf-8')

            print(f"      Rows: {len(df):,} | Columns: {len(df.columns)}")
            return True
        except Exception as e:
            print(f"      ⚠️  Error: {e}")
            return False

    def upload_csv(self, csv_path: Path, table_name: str):
        """Upload CSV file to Keboola"""
        full_table_id = f"{self.bucket_id}.{table_name}"

        print(f"   Uploading {table_name}...")

        try:
            # Check if table exists
            try:
                self.client.tables.detail(full_table_id)
                # Table exists, replace data
                self.client.tables.load(
                    table_id=full_table_id,
                    file_path=str(csv_path),
                    is_incremental=False
                )
                print(f"      ✓ Updated")
            except Exception:
                # Table doesn't exist, create it
                self.client.tables.create(
                    name=table_name,
                    bucket_id=self.bucket_id,
                    file_path=str(csv_path)
                )
                print(f"      ✓ Created")

            return True
        except Exception as e:
            print(f"      ✗ Error: {e}")
            return False

    def load_dataset(self, dataset_key: str):
        """Load a dataset to Keboola"""
        dataset = self.config['datasets'][dataset_key]
        prefix = dataset['keboola_prefix']
        encoding = dataset['encoding']

        dataset_dir = self.output_dir / dataset_key
        if not dataset_dir.exists():
            print(f"⚠️  Dataset directory not found: {dataset_dir}")
            return

        # Find all CSV files
        csv_files = list(dataset_dir.glob('*.csv'))

        if not csv_files:
            print(f"⚠️  No CSV files found in {dataset_dir}")
            return

        print(f"\n🚀 Loading {dataset['name']} to Keboola")
        print(f"   Dataset: {dataset_key}")
        print(f"   Files: {len(csv_files)}")
        print(f"   Bucket: {self.bucket_id}")
        print()

        # Ensure bucket exists
        self.ensure_bucket()

        # Process each CSV
        converted_dir = self.output_dir / f"{dataset_key}_converted"
        converted_dir.mkdir(exist_ok=True)

        success_count = 0
        for csv_file in sorted(csv_files):
            # Convert to UTF-8
            output_file = converted_dir / csv_file.name
            if self.convert_csv(csv_file, output_file, encoding):
                # Upload to Keboola
                # Create table name: prefix_filename (without .csv)
                table_name = f"{prefix}_{csv_file.stem}"
                if self.upload_csv(output_file, table_name):
                    success_count += 1

        print()
        print("=" * 60)
        print(f"✅ Upload Summary:")
        print(f"   Uploaded: {success_count}/{len(csv_files)} tables")
        print(f"   Bucket: {self.bucket_id}")
        print("=" * 60)


def main():
    """Main entry point"""
    import sys

    loader = SUKLLoader()

    if len(sys.argv) > 1:
        dataset_key = sys.argv[1]
    else:
        dataset_key = 'dlp'  # Default to DLP

    print(f"\n🚀 SÚKL Data Loader")
    print(f"Dataset: {dataset_key}\n")

    loader.load_dataset(dataset_key)


if __name__ == '__main__':
    main()

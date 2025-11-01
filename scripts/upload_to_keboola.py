#!/usr/bin/env python3
"""Upload Datagen CSV exports to Keboola Connection.

Usage:
    python upload_to_keboola.py [csv_dir] [bucket_name]

Examples:
    # With environment variables
    export KEBOOLA_TOKEN="your-token-here"
    python upload_to_keboola.py output_csv

    # With .env file (recommended)
    # Create .env with KEBOOLA_URL and KEBOOLA_TOKEN
    python upload_to_keboola.py output_csv

    # Upload to specific bucket
    python upload_to_keboola.py output_csv my-datagen-bucket

    # Upload to staging bucket
    python upload_to_keboola.py output_csv datagen-staging
"""

import os
import sys
import json
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Look for .env in current directory and parent directories
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📄 Loaded credentials from .env file")
    else:
        # Try parent directory (common when running from subdirectory)
        parent_env = Path('..') / '.env'
        if parent_env.exists():
            load_dotenv(parent_env)
            print(f"📄 Loaded credentials from ../.env file")
except ImportError:
    # python-dotenv not installed, will use environment variables
    pass

try:
    from kbcstorage.client import Client
except ImportError:
    print("❌ Error: kbcstorage module not found")
    print("Install it with: pip install kbcstorage")
    sys.exit(1)

# Configuration
# KEBOOLA_URL: Your Keboola instance URL
#   - US: https://connection.keboola.com
#   - EU: https://connection.eu-central-1.keboola.com
#   - Other regions: Check your Keboola login URL
KEBOOLA_URL = os.environ.get("KEBOOLA_URL", "https://connection.keboola.com")

# KEBOOLA_TOKEN: Your Storage API token
#   - Get from: Keboola UI → Settings → API Tokens
#   - Needs "Storage" read/write permissions
KEBOOLA_TOKEN = os.environ.get("KEBOOLA_TOKEN")

DEFAULT_CSV_DIR = "output_csv"
DEFAULT_BUCKET_NAME = "datagen"
DEFAULT_BUCKET_STAGE = "in"


def upload_to_keboola(csv_dir: str, bucket_name: str, bucket_stage: str = "in"):
    """Upload all CSV files with manifests to Keboola.

    Args:
        csv_dir: Directory containing CSV files and manifests
        bucket_name: Name of the Keboola bucket (without stage prefix)
        bucket_stage: Bucket stage ('in' or 'out')

    Returns:
        0 on success, 1 on error
    """

    if not KEBOOLA_TOKEN:
        print("❌ Error: KEBOOLA_TOKEN environment variable not set")
        print("Set it with: export KEBOOLA_TOKEN='your-token-here'")
        print("\nTo get your token:")
        print("1. Log in to Keboola Connection")
        print("2. Go to Settings → API Tokens")
        print("3. Create a new token or copy existing one")
        return 1

    csv_path = Path(csv_dir)
    if not csv_path.exists():
        print(f"❌ Error: Directory {csv_dir} does not exist")
        return 1

    # Initialize client
    print(f"📡 Connecting to Keboola...")
    print(f"   URL: {KEBOOLA_URL}")

    try:
        client = Client(KEBOOLA_URL, KEBOOLA_TOKEN)
        # Verify token
        token_info = client.tokens.verify()
        print(f"   ✓ Connected as: {token_info.get('description', 'Unknown')}")
    except Exception as e:
        print(f"❌ Error connecting to Keboola: {e}")
        return 1

    # Create bucket if it doesn't exist
    bucket_id = f"{bucket_stage}.c-{bucket_name}"
    print(f"\n📦 Checking bucket: {bucket_id}")

    try:
        bucket = client.buckets.detail(bucket_id)
        print(f"   ✓ Bucket exists")
    except:
        print(f"   Creating bucket...")
        try:
            client.buckets.create(
                name=bucket_name,
                stage=bucket_stage,
                description=f"Synthetic data from Datagen"
            )
            print(f"   ✓ Created bucket: {bucket_id}")
        except Exception as e:
            print(f"❌ Error creating bucket: {e}")
            return 1

    # Read dataset metadata if available
    dataset_meta_path = csv_path / "dataset.json"
    if dataset_meta_path.exists():
        try:
            with open(dataset_meta_path) as f:
                dataset_meta = json.load(f)
            print(f"\n📋 Dataset Information:")
            print(f"   Name: {dataset_meta.get('dataset_name', 'Unknown')}")
            print(f"   Version: {dataset_meta.get('version', 'Unknown')}")
            if 'generation_stats' in dataset_meta:
                stats = dataset_meta['generation_stats']
                print(f"   Tables: {stats.get('total_tables', 'Unknown')}")
                print(f"   Total Rows: {stats.get('total_rows', 'Unknown'):,}")
        except Exception as e:
            print(f"⚠️  Warning: Could not read dataset.json: {e}")

    # Find all CSV files
    csv_files = sorted(csv_path.glob("*.csv"))
    if not csv_files:
        print(f"\n❌ Error: No CSV files found in {csv_dir}")
        return 1

    print(f"\n🔄 Uploading {len(csv_files)} tables...\n")

    uploaded = 0
    failed = 0

    for csv_file in csv_files:
        table_name = csv_file.stem
        manifest_file = csv_file.parent / f"{csv_file.name}.manifest"

        # Read manifest for metadata
        primary_key = []
        if manifest_file.exists():
            try:
                with open(manifest_file) as f:
                    manifest = json.load(f)
                    primary_key = manifest.get("primary_key", [])
            except Exception as e:
                print(f"  ⚠️  {table_name}: Could not read manifest ({e})")

        print(f"  {table_name}...", end=" ", flush=True)

        try:
            # Check if table exists
            table_id = f"{bucket_id}.{table_name}"
            table_exists = False

            try:
                client.tables.detail(table_id)
                table_exists = True
            except:
                pass

            if table_exists:
                # Update existing table
                client.tables.load(
                    table_id=table_id,
                    file_path=str(csv_file),
                    is_incremental=False  # Full load
                )
                print(f"✓ Updated")
            else:
                # Create new table
                client.tables.create(
                    name=table_name,
                    bucket_id=bucket_id,
                    file_path=str(csv_file),
                    primary_key=primary_key
                )
                pk_str = f" (PK: {primary_key})" if primary_key else ""
                print(f"✓ Created{pk_str}")

            uploaded += 1

        except Exception as e:
            print(f"❌ Failed: {e}")
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Upload Summary:")
    print(f"   Uploaded: {uploaded}/{len(csv_files)} tables")
    if failed > 0:
        print(f"   Failed: {failed}")
    print(f"   Bucket: {bucket_id}")
    print(f"   View at: {KEBOOLA_URL}")
    print(f"{'='*60}")

    return 0 if failed == 0 else 1


def main():
    """Main entry point."""

    # Parse arguments
    csv_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV_DIR
    bucket_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BUCKET_NAME
    bucket_stage = DEFAULT_BUCKET_STAGE

    # Show usage if help requested
    if csv_dir in ["-h", "--help", "help"]:
        print(__doc__)
        return 0

    print("="*60)
    print("Datagen → Keboola Connection Upload")
    print("="*60)
    print(f"CSV Directory: {csv_dir}")
    print(f"Target Bucket: {bucket_stage}.c-{bucket_name}")
    print("="*60)

    return upload_to_keboola(csv_dir, bucket_name, bucket_stage)


if __name__ == "__main__":
    sys.exit(main())

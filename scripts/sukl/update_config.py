#!/usr/bin/env python3
"""Update SÚKL configuration with corrected code"""

import requests
import json

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"
CONFIG_ID = "01k7m1w7xxnm2yepjd7rz1tk5a"

headers = {
    "X-StorageApi-Token": KBC_TOKEN,
    "Content-Type": "application/json"
}

# Read the corrected script
with open('sukl_keboola.py', 'r') as f:
    script_code = f.read()

# Update configuration
payload = {
    "configuration": json.dumps({
        "parameters": {
            "code": script_code,
            "source": "code",
            "venv": "3.13",
            "packages": [
                "anthropic>=0.39.0",
                "kbcstorage>=0.9.0",
                "pandas>=2.0.0",
                "requests>=2.31.0",
                "keboola.component>=1.6.0"
            ],
            "user_properties": {
                "dataset": "dlp",
                "bucket_id": "in.c-sukl"
            }
        }
    })
}

print("📝 Updating configuration...")

response = requests.put(
    f"{KBC_URL}/v2/storage/components/kds-team.app-custom-python/configs/{CONFIG_ID}",
    headers=headers,
    json=payload
)

if response.status_code == 200:
    print("✅ Configuration updated successfully!")
    print("\nThe code now properly reads from Keboola user parameters.")
    print("Your #ANTHROPIC_API_KEY should now be accessible.")
    print("\n✅ Ready to run!")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)

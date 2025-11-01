#!/usr/bin/env python3
import requests
import json

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"

headers = {"X-StorageApi-Token": KBC_TOKEN}

response = requests.get(
    f"{KBC_URL}/v2/storage/components/kds-team.app-custom-python/configs/01k7m1w7xxnm2yepjd7rz1tk5a",
    headers=headers
)

if response.status_code == 200:
    config = response.json()
    print("Current configuration:")
    print(json.dumps(config.get('configuration', {}), indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)

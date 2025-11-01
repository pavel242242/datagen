#!/usr/bin/env python3
import requests

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"

headers = {"X-StorageApi-Token": KBC_TOKEN}

response = requests.get(f"{KBC_URL}/v2/storage/jobs?limit=10", headers=headers)

if response.status_code == 200:
    jobs = response.json()
    print(f"Found {len(jobs)} recent jobs:\n")
    for j in jobs:
        comp = j.get('component', 'N/A')
        config_id = j.get('configId') or j.get('config', {}).get('id', 'N/A')
        status = j.get('status', 'N/A')
        print(f"  {j['id']}: {comp} (config: {config_id}) - {status}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

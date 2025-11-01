#!/usr/bin/env python3
import requests
import json
import sys

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"

headers = {"X-StorageApi-Token": KBC_TOKEN}

job_id = sys.argv[1] if len(sys.argv) > 1 else "30541690"

response = requests.get(f"{KBC_URL}/queue/jobs/{job_id}", headers=headers)

if response.status_code == 200:
    job = response.json()
    print(json.dumps(job, indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)

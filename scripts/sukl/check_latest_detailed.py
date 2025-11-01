#!/usr/bin/env python3
import requests
import json

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"

headers = {"X-StorageApi-Token": KBC_TOKEN}

response = requests.get(f"{KBC_URL}/v2/storage/jobs?limit=3", headers=headers)

if response.status_code == 200:
    jobs = response.json()
    print(f"Latest 3 jobs:\n")
    for j in jobs[:3]:
        print(f"Job {j['id']}:")
        print(json.dumps(j, indent=2))
        print("\n" + "="*70 + "\n")
else:
    print(f"Error: {response.status_code}")

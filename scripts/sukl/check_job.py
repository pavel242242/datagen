#!/usr/bin/env python3
"""Check latest job status and logs"""

import requests
import json

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"
CONFIG_ID = "01k7m1w7xxnm2yepjd7rz1tk5a"

headers = {"X-StorageApi-Token": KBC_TOKEN}

# Get latest jobs
print("🔍 Checking latest jobs...\n")

response = requests.get(
    f"{KBC_URL}/v2/storage/components/kds-team.app-custom-python/configs/{CONFIG_ID}/jobs",
    headers=headers
)

if response.status_code == 200:
    jobs = response.json()

    if jobs:
        latest = jobs[0]
        print(f"Latest Job ID: {latest['id']}")
        print(f"Status: {latest['status']}")
        print(f"Started: {latest.get('startTime', 'N/A')}")
        print(f"Ended: {latest.get('endTime', 'N/A')}")

        if latest.get('result'):
            print(f"\n📊 Result:")
            print(json.dumps(latest['result'], indent=2))

        # Get detailed job info with logs
        print(f"\n📋 Getting job details...")
        job_response = requests.get(
            f"{KBC_URL}/v2/storage/jobs/{latest['id']}",
            headers=headers
        )

        if job_response.status_code == 200:
            job_detail = job_response.json()

            if job_detail.get('error'):
                print(f"\n❌ Error:")
                print(json.dumps(job_detail['error'], indent=2))

            # Show last part of logs
            if job_detail.get('logs'):
                logs = job_detail['logs']
                print(f"\n📜 Logs (last 2000 chars):")
                print("="*70)
                print(logs[-2000:])
                print("="*70)
    else:
        print("No jobs found")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

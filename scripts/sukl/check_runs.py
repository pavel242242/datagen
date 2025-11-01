#!/usr/bin/env python3
"""Check job runs for the configuration"""

import requests
import json

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"

headers = {"X-StorageApi-Token": KBC_TOKEN}

# Try queue API
print("🔍 Checking queue/jobs...\n")

response = requests.get(
    f"{KBC_URL}/queue/jobs?component=kds-team.app-custom-python&config=01k7m1w7xxnm2yepjd7rz1tk5a&limit=1",
    headers=headers
)

if response.status_code == 200:
    jobs = response.json()

    if jobs:
        latest = jobs[0]
        print(f"Job ID: {latest['id']}")
        print(f"Status: {latest['status']}")
        print(f"Created: {latest.get('createdTime', 'N/A')}")

        if latest.get('result'):
            print(f"\n📊 Result:")
            result = latest['result']
            if result.get('message'):
                print(f"Message: {result['message']}")

        # Get job detail
        print(f"\n📋 Getting job details...")
        job_response = requests.get(
            f"{KBC_URL}/queue/jobs/{latest['id']}",
            headers=headers
        )

        if job_response.status_code == 200:
            job_detail = job_response.json()

            print(f"\nStatus: {job_detail.get('status')}")

            if job_detail.get('result', {}).get('message'):
                print(f"\n❌ Error Message:")
                print(job_detail['result']['message'])

            # Get logs URL
            if job_detail.get('url'):
                print(f"\nLogs URL: {job_detail['url']}")
        else:
            print(f"Error getting job detail: {job_response.status_code}")
    else:
        print("No jobs found")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

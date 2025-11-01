#!/usr/bin/env python3
"""
Continuously watch for SÚKL jobs and auto-report errors
"""

import requests
import json
import time

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"
CONFIG_ID = "01k7m1w7xxnm2yepjd7rz1tk5a"

headers = {"X-StorageApi-Token": KBC_TOKEN}

seen_jobs = set()

def check_jobs():
    """Check for new jobs"""
    response = requests.get(
        f"{KBC_URL}/v2/storage/jobs?limit=20",
        headers=headers
    )

    if response.status_code != 200:
        return []

    jobs = response.json()

    # Filter for our config
    our_jobs = []
    for job in jobs:
        config_id = job.get('configId') or job.get('config', {}).get('id')
        if config_id == CONFIG_ID:
            our_jobs.append(job)

    return our_jobs

def main():
    print("="*70)
    print("👀 Watching for SÚKL Extractor jobs...")
    print("="*70)
    print("\n💡 Run the SÚKL Data Extractor in Keboola UI now")
    print("   I'll automatically detect and report on it\n")

    while True:
        jobs = check_jobs()

        for job in jobs:
            job_id = job.get('id')

            if job_id in seen_jobs:
                continue

            seen_jobs.add(job_id)

            status = job.get('status')

            print(f"\n{'='*70}")
            print(f"📋 New job detected: {job_id}")
            print(f"   Status: {status}")

            if status in ['waiting', 'processing', 'running']:
                print(f"   ⏳ Job is running...")

            elif status == 'success':
                print(f"   ✅ SUCCESS!")
                result = job.get('result', {})
                if result:
                    print(f"   Result: {json.dumps(result, indent=2)}")
                print(f"\n   📊 Check Storage bucket 'in.c-sukl' for tables!")

            elif status == 'error':
                print(f"   ❌ FAILED")

                result = job.get('result', {})
                error_msg = result.get('message', 'Unknown error')

                print(f"\n   Error message:")
                if 'Traceback' in error_msg:
                    lines = error_msg.split('\\n')
                    for line in lines[-15:]:
                        if line.strip():
                            print(f"     {line}")
                else:
                    print(f"     {error_msg}")

                print(f"\n   💡 I can help fix this error!")

        time.sleep(3)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching")

#!/usr/bin/env python3
"""
Monitor latest job - check status, show errors, offer to fix
"""

import requests
import json
import time

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"
COMPONENT_ID = "kds-team.app-custom-python"
CONFIG_ID = "01k7m1w7xxnm2yepjd7rz1tk5a"

headers = {"X-StorageApi-Token": KBC_TOKEN}

def get_latest_job():
    """Get latest job for this config"""
    # Try to get job via storage API
    response = requests.get(
        f"{KBC_URL}/v2/storage/jobs?component={COMPONENT_ID}&limit=10",
        headers=headers
    )

    if response.status_code == 200:
        jobs = response.json()
        # Filter for our config
        for job in jobs:
            config_id = job.get('configId') or job.get('config', {}).get('id')
            if config_id == CONFIG_ID:
                return job
    return None

def wait_for_completion(initial_job_id):
    """Wait for job to complete"""
    print(f"⏳ Monitoring job...")

    last_status = None

    while True:
        job = get_latest_job()

        if not job:
            print("  No job found")
            time.sleep(3)
            continue

        job_id = job.get('id')
        status = job.get('status')

        # Different job started
        if job_id != initial_job_id:
            print(f"\n🔄 New job detected: {job_id}")
            initial_job_id = job_id

        # Status changed
        if status != last_status:
            print(f"  Status: {status}")
            last_status = status

        # Job finished
        if status in ['success', 'error', 'terminated', 'cancelled']:
            return job

        time.sleep(3)

def main():
    print("="*70)
    print("👀 SÚKL Job Monitor")
    print("="*70)

    print("\n📋 Getting latest job...")

    latest = get_latest_job()

    if not latest:
        print("❌ No jobs found")
        print("\n💡 Please run the SÚKL Data Extractor in Keboola UI first")
        return

    job_id = latest.get('id')
    status = latest.get('status')

    print(f"\nJob ID: {job_id}")
    print(f"Status: {status}")

    if status in ['waiting', 'processing', 'running']:
        print("\n⏳ Job is running, waiting for completion...")
        final_job = wait_for_completion(job_id)
    else:
        final_job = latest

    status = final_job.get('status')

    print("\n" + "="*70)

    if status == 'success':
        print("✅ SUCCESS!")
        print("="*70)

        result = final_job.get('result', {})
        print(f"\nResult: {json.dumps(result, indent=2)}")

        print("\n📊 Check Storage bucket 'in.c-sukl' for tables!")

    elif status == 'error':
        print("❌ JOB FAILED")
        print("="*70)

        # Get error details
        result = final_job.get('result', {})
        error_msg = result.get('message', 'Unknown error')

        print(f"\nError:\n{error_msg}")

        # Try to extract the actual error
        if 'Traceback' in error_msg:
            lines = error_msg.split('\\n')
            print("\n📋 Error Details:")
            for line in lines:
                if line.strip():
                    print(f"  {line}")

    else:
        print(f"⚠️  Job ended with status: {status}")
        print("="*70)

if __name__ == '__main__':
    main()

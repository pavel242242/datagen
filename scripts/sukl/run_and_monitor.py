#!/usr/bin/env python3
"""
Run SÚKL job via API and monitor it
"""

import requests
import json
import time

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"
COMPONENT_ID = "kds-team.app-custom-python"
CONFIG_ID = "01k7m1w7xxnm2yepjd7rz1tk5a"

headers = {"X-StorageApi-Token": KBC_TOKEN, "Content-Type": "application/json"}

def run_component():
    """Run the component configuration"""
    print("🚀 Starting SÚKL extraction job...")

    # Try the run endpoint
    payload = {"config": CONFIG_ID}

    response = requests.post(
        f"{KBC_URL}/v2/storage/components/{COMPONENT_ID}/configs/{CONFIG_ID}/run",
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201, 202]:
        job = response.json()
        job_id = job.get('id')
        print(f"✓ Job started: {job_id}")
        return job_id
    else:
        print(f"❌ Failed to start: {response.status_code}")
        print(response.text)
        return None

def get_job_status(job_id):
    """Get job status"""
    response = requests.get(
        f"{KBC_URL}/v2/storage/jobs/{job_id}",
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    return None

def monitor_job(job_id):
    """Monitor job until completion"""
    print(f"\n⏳ Monitoring job {job_id}...")

    while True:
        job = get_job_status(job_id)

        if not job:
            print("  ⚠️ Could not get job status")
            time.sleep(3)
            continue

        status = job.get('status')
        print(f"  Status: {status}")

        if status in ['success', 'error', 'terminated', 'cancelled']:
            return job

        time.sleep(5)

def show_result(job):
    """Show job result"""
    status = job.get('status')

    print("\n" + "="*70)

    if status == 'success':
        print("✅ SUCCESS!")
        print("="*70)

        result = job.get('result', {})
        if result:
            print(f"\n{json.dumps(result, indent=2)}")

        print("\n📊 Check bucket 'in.c-sukl' in Keboola Storage!")
        return True

    elif status == 'error':
        print("❌ FAILED")
        print("="*70)

        result = job.get('result', {})
        error_msg = result.get('message', 'Unknown error')

        print(f"\n{error_msg}")

        # Extract traceback if present
        if 'Traceback' in error_msg:
            print("\n📋 Extracted error:")
            lines = error_msg.split('\\n')
            for line in lines[-10:]:  # Last 10 lines
                if line.strip():
                    print(f"  {line}")

        return False

    return False

def main():
    print("="*70)
    print("🚀 SÚKL Extractor - Run & Monitor")
    print("="*70 + "\n")

    # Run the job
    job_id = run_component()

    if not job_id:
        print("\n❌ Could not start job")
        return

    # Monitor until completion
    final_job = monitor_job(job_id)

    # Show result
    success = show_result(final_job)

    if not success:
        print("\n💡 Would you like me to try to fix the error? (manual fix needed)")

if __name__ == '__main__':
    main()

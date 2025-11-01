#!/usr/bin/env python3
"""
Automated debug loop for SÚKL extractor
Run → Wait → Check errors → Ask for fix → Deploy → Repeat
"""

import requests
import json
import time

KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"
COMPONENT_ID = "kds-team.app-custom-python"
CONFIG_ID = "01k7m1w7xxnm2yepjd7rz1tk5a"

headers = {"X-StorageApi-Token": KBC_TOKEN}

def run_job():
    """Trigger a job run"""
    print("\n🚀 Starting job...")

    # Use the docker-runner API endpoint
    payload = {
        "config": CONFIG_ID,
        "component": COMPONENT_ID
    }

    response = requests.post(
        f"{KBC_URL}/docker/{COMPONENT_ID}/run",
        headers={**headers, "Content-Type": "application/json"},
        json=payload
    )

    if response.status_code in [200, 201, 202]:
        job_data = response.json()
        job_id = job_data.get('id')
        print(f"✓ Job started: {job_id}")
        return job_id
    else:
        print(f"❌ Failed to start job: {response.status_code}")
        print(response.text)
        return None

def wait_for_job(job_id, max_wait=600):
    """Wait for job to complete"""
    print(f"⏳ Waiting for job {job_id} to complete...")

    start_time = time.time()

    while time.time() - start_time < max_wait:
        response = requests.get(
            f"{KBC_URL}/v2/storage/jobs/{job_id}",
            headers=headers
        )

        if response.status_code == 200:
            job = response.json()
            status = job.get('status')

            if status in ['success', 'terminated', 'error', 'cancelled']:
                return job

            # Still running
            print(f"  Status: {status} ({int(time.time() - start_time)}s)")
            time.sleep(5)
        else:
            print(f"⚠️ Error checking status: {response.status_code}")
            time.sleep(5)

    print("⏰ Timeout waiting for job")
    return None

def extract_error(job_data):
    """Extract error message from job data"""
    result = job_data.get('result', {})

    # Try to get error message
    if result.get('message'):
        return result['message']

    # Try to get from error object
    error = job_data.get('error', {})
    if error:
        return json.dumps(error, indent=2)

    return "Unknown error"

def update_code(new_code):
    """Update configuration with new code"""
    print("\n📝 Deploying updated code...")

    with open('sukl_keboola.py', 'w') as f:
        f.write(new_code)

    payload = {
        "configuration": json.dumps({
            "parameters": {
                "code": new_code,
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

    response = requests.put(
        f"{KBC_URL}/v2/storage/components/{COMPONENT_ID}/configs/{CONFIG_ID}",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        print("✅ Code deployed")
        return True
    else:
        print(f"❌ Deploy failed: {response.status_code}")
        print(response.text)
        return False

def main():
    """Main debug loop"""
    print("="*70)
    print("🔧 SÚKL Extractor - Auto Debug Loop")
    print("="*70)

    max_attempts = 5
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        print(f"\n{'='*70}")
        print(f"Attempt {attempt}/{max_attempts}")
        print("="*70)

        # Run job
        job_id = run_job()
        if not job_id:
            print("❌ Failed to start job")
            break

        # Wait for completion
        job_data = wait_for_job(job_id)
        if not job_data:
            print("❌ Job timeout or error")
            break

        status = job_data.get('status')

        if status == 'success':
            print("\n" + "="*70)
            print("✅ SUCCESS! Job completed successfully!")
            print("="*70)

            # Check results
            result = job_data.get('result', {})
            print(f"\nResult: {json.dumps(result, indent=2)}")

            # TODO: Check if tables were created
            print("\n📊 Check Keboola Storage bucket 'in.c-sukl' for tables")
            break

        elif status == 'error':
            print("\n❌ Job failed with error")

            # Extract error
            error_msg = extract_error(job_data)
            print("\n📋 Error Details:")
            print("="*70)
            print(error_msg)
            print("="*70)

            # Ask user for fix
            print("\n💡 Would you like to:")
            print("1. Let me try to auto-fix this error")
            print("2. Show me the current code")
            print("3. Retry without changes")
            print("4. Stop")

            choice = input("\nChoice (1-4): ").strip()

            if choice == '1':
                # TODO: Use Claude to fix the error
                print("\n🤖 Auto-fix not implemented yet")
                print("Please fix the error manually in sukl_keboola.py")

                input("Press Enter when code is fixed...")

                # Read updated code
                with open('sukl_keboola.py', 'r') as f:
                    new_code = f.read()

                # Deploy
                if update_code(new_code):
                    print("✅ Retrying with fixed code...")
                    continue
                else:
                    break

            elif choice == '2':
                print("\n📄 Current code:")
                with open('sukl_keboola.py', 'r') as f:
                    print(f.read())
                break

            elif choice == '3':
                print("🔄 Retrying...")
                time.sleep(2)
                continue

            else:
                print("🛑 Stopping")
                break

        else:
            print(f"\n⚠️ Unexpected status: {status}")
            break

    if attempt >= max_attempts:
        print("\n⚠️ Max attempts reached")

if __name__ == '__main__':
    main()

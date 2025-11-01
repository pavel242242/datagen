#!/usr/bin/env python3
"""
Create SÚKL Extractor configuration in Keboola via API
"""

import os
import requests
import json

# Keboola credentials
KBC_URL = "https://connection.us-east4.gcp.keboola.com"
KBC_TOKEN = "2929-1172770-lgYALX8oVhmtebgp9mbFWJ032SMDWHge6hmqbd2i"

# API headers
headers = {
    "X-StorageApi-Token": KBC_TOKEN,
    "Content-Type": "application/json"
}

def list_components():
    """List available components"""
    print("🔍 Searching for Python components...")

    # Use the Docker Runner API to list components
    response = requests.get(
        f"{KBC_URL}/v2/storage/components",
        headers=headers
    )

    if response.status_code == 200:
        components = response.json()
        python_comps = [c for c in components if 'python' in c.get('id', '').lower() or 'python' in c.get('name', '').lower()]

        print(f"\nFound {len(python_comps)} Python components:")
        for comp in python_comps:
            print(f"  - {comp.get('id')}: {comp.get('name', 'N/A')}")

        return python_comps
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return []

def list_configurations(component_id):
    """List configurations for a component"""
    print(f"\n📋 Configurations for {component_id}:")

    response = requests.get(
        f"{KBC_URL}/v2/storage/components/{component_id}/configs",
        headers=headers
    )

    if response.status_code == 200:
        configs = response.json()
        for cfg in configs:
            print(f"  - {cfg.get('name')} (ID: {cfg.get('id')})")
        return configs
    else:
        print(f"❌ Error: {response.status_code}")
        return []

def create_configuration(component_id, name, description):
    """Create a new configuration"""
    print(f"\n✨ Creating configuration: {name}")

    payload = {
        "name": name,
        "description": description
    }

    response = requests.post(
        f"{KBC_URL}/v2/storage/components/{component_id}/configs",
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201]:
        config = response.json()
        print(f"✅ Created configuration ID: {config.get('id')}")
        return config
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

def update_configuration(component_id, config_id, code, env_vars):
    """Update configuration with code and parameters"""
    print(f"\n📝 Updating configuration {config_id}...")

    # Read the Python script
    script_path = "sukl_extractor_simple.py"
    with open(script_path, 'r') as f:
        script_code = f.read()

    payload = {
        "configuration": json.dumps({
            "parameters": {
                "script": script_code.split('\n'),
                "packages": [
                    "anthropic>=0.39.0",
                    "kbcstorage>=0.9.0",
                    "pandas>=2.0.0",
                    "requests>=2.31.0"
                ]
            },
            "runtime": {
                "env": env_vars
            }
        })
    }

    response = requests.put(
        f"{KBC_URL}/v2/storage/components/{component_id}/configs/{config_id}",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        print("✅ Configuration updated")
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return False

def main():
    print("="*70)
    print("🚀 SÚKL Keboola Configuration Setup")
    print("="*70)

    # Step 1: List Python components
    components = list_components()

    if not components:
        print("\n⚠️  No Python components found. You may need to:")
        print("   1. Use Keboola's Python Transformation component")
        print("   2. Or use Generic Docker Runner with Python image")
        return

    # Try to find keboola.python-transformation-v2 or similar
    python_comp = None
    for comp in components:
        if 'transformation' in comp.get('id', '').lower() and 'python' in comp.get('id', '').lower():
            python_comp = comp
            break

    if not python_comp and components:
        python_comp = components[0]  # Use first Python component

    component_id = python_comp['id']
    print(f"\n✅ Using component: {component_id}")

    # Step 2: List existing configurations
    list_configurations(component_id)

    # Step 3: Create new configuration
    config = create_configuration(
        component_id,
        "SUKL Data Extractor",
        "AI-powered extraction of Czech pharmaceutical data from opendata.sukl.cz"
    )

    if not config:
        print("\n❌ Failed to create configuration")
        return

    # Step 4: Update with code and env vars
    env_vars = {
        "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_KEY",  # User needs to set this
        "KBC_TOKEN": KBC_TOKEN,
        "KBC_URL": KBC_URL,
        "DATASET": "dlp"
    }

    update_configuration(component_id, config['id'], "", env_vars)

    print("\n" + "="*70)
    print("✅ Configuration created!")
    print(f"   Component: {component_id}")
    print(f"   Config ID: {config['id']}")
    print(f"   Name: SUKL Data Extractor")
    print("\n⚠️  Remember to set your ANTHROPIC_API_KEY in the configuration!")
    print("="*70)

if __name__ == '__main__':
    main()

# Keboola Credentials Setup

## What You Need

To upload data to Keboola, you need **2 things**:

1. **Endpoint URL** - Your Keboola instance URL
2. **Storage API Token** - Authentication token with write permissions

---

## 1. Find Your Keboola Endpoint

Your endpoint is the URL you use to log in to Keboola.

### Common Endpoints

| Region | Endpoint URL |
|--------|--------------|
| **US** | `https://connection.keboola.com` |
| **EU (Central)** | `https://connection.eu-central-1.keboola.com` |
| **EU (North)** | `https://connection.north-europe.azure.keboola.com` |
| **Azure US** | `https://connection.east-us-2.azure.keboola.com` |

### How to Find Your Endpoint

1. **Look at your Keboola login URL**
   - The URL you use to access Keboola IS your endpoint
   - Example: If you go to `https://connection.keboola.com` → your endpoint is `https://connection.keboola.com`

2. **Check your browser address bar** when logged in
   - The domain (without `/admin/projects/...`) is your endpoint

3. **Ask your Keboola admin** if you're not sure

---

## 2. Get Your Storage API Token

### Step-by-Step Instructions

1. **Log in to Keboola Connection**
   - Go to your Keboola endpoint URL
   - Sign in with your credentials

2. **Navigate to API Tokens**
   - Click on **Settings** (gear icon) in the top right
   - Select **API Tokens** from the menu
   - Or go directly to: `https://YOUR-ENDPOINT/admin/projects/YOUR-PROJECT/settings-tokens`

3. **Create a New Token**
   - Click **New Token**
   - Fill in the details:
     - **Description**: "Datagen Upload Script" (or any name you prefer)
     - **Permissions**: Check **Storage** → **Read** and **Write**
   - Click **Create Token**

4. **Copy the Token**
   - **IMPORTANT**: Copy the token immediately!
   - You won't be able to see it again after closing the dialog
   - Store it securely (like a password)

### Token Example

Your token will look something like this:
```
1234-567890-abcdefghijklmnopqrstuvwxyz
```

### Token Permissions Required

For uploading data, your token needs:
- ✅ **Storage → Read** (to check if tables exist)
- ✅ **Storage → Write** (to create/update tables)

Optional but recommended:
- ✅ **Storage → Manage** (to create buckets)

---

## 3. Set Environment Variables

### Method 1: Command Line (Temporary)

**macOS / Linux:**
```bash
export KEBOOLA_URL="https://connection.keboola.com"
export KEBOOLA_TOKEN="your-token-here"
```

**Windows (PowerShell):**
```powershell
$env:KEBOOLA_URL = "https://connection.keboola.com"
$env:KEBOOLA_TOKEN = "your-token-here"
```

**Windows (CMD):**
```cmd
set KEBOOLA_URL=https://connection.keboola.com
set KEBOOLA_TOKEN=your-token-here
```

### Method 2: .env File (Persistent)

Create a `.env` file in your project root:

```bash
# .env file
KEBOOLA_URL=https://connection.keboola.com
KEBOOLA_TOKEN=1234-567890-abcdefghijklmnopqrstuvwxyz
```

**IMPORTANT**: Add `.env` to your `.gitignore`:
```bash
echo ".env" >> .gitignore
```

Load the environment variables:

**macOS / Linux:**
```bash
source .env
```

**Or use with Python:**
```python
from dotenv import load_dotenv
load_dotenv()

# Install python-dotenv first:
# pip install python-dotenv
```

### Method 3: Configuration File

Create `keboola_config.json`:

```json
{
  "url": "https://connection.keboola.com",
  "token": "your-token-here"
}
```

**IMPORTANT**: Add `keboola_config.json` to `.gitignore`

---

## 4. Verify Your Setup

### Test Connection

```bash
# Set your credentials
export KEBOOLA_URL="https://connection.keboola.com"
export KEBOOLA_TOKEN="your-token-here"

# Test with curl
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  "$KEBOOLA_URL/v2/storage/tokens/verify"
```

**Expected Response:**
```json
{
  "id": "12345",
  "description": "Datagen Upload Script",
  "created": "2024-01-15 10:30:00",
  "isDisabled": false,
  "owner": {
    "id": "67890",
    "name": "Your Name"
  }
}
```

**If you get an error:**
- `401 Unauthorized` → Token is invalid or expired
- `Connection refused` → Wrong endpoint URL
- `403 Forbidden` → Token doesn't have required permissions

### Test with Python

```python
from kbcstorage.client import Client
import os

url = os.environ.get("KEBOOLA_URL", "https://connection.keboola.com")
token = os.environ.get("KEBOOLA_TOKEN")

if not token:
    print("❌ KEBOOLA_TOKEN not set!")
    exit(1)

try:
    client = Client(url, token)
    token_info = client.tokens.verify()
    print(f"✅ Connected successfully!")
    print(f"   Description: {token_info.get('description')}")
    print(f"   Owner: {token_info.get('owner', {}).get('name')}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

---

## 5. Use in Scripts

### Python Upload Script

```python
#!/usr/bin/env python3
import os
from kbcstorage.client import Client

# Read from environment variables
KEBOOLA_URL = os.environ.get("KEBOOLA_URL", "https://connection.keboola.com")
KEBOOLA_TOKEN = os.environ.get("KEBOOLA_TOKEN")

if not KEBOOLA_TOKEN:
    print("❌ Error: KEBOOLA_TOKEN environment variable not set")
    exit(1)

# Connect to Keboola
client = Client(KEBOOLA_URL, KEBOOLA_TOKEN)

# Your upload code here...
```

### Shell Script

```bash
#!/bin/bash

# Check if credentials are set
if [ -z "$KEBOOLA_URL" ]; then
    echo "❌ KEBOOLA_URL not set"
    exit 1
fi

if [ -z "$KEBOOLA_TOKEN" ]; then
    echo "❌ KEBOOLA_TOKEN not set"
    exit 1
fi

echo "✅ Credentials found"
echo "   URL: $KEBOOLA_URL"
echo "   Token: ${KEBOOLA_TOKEN:0:10}..." # Show only first 10 chars

# Your upload code here...
```

---

## 6. Complete Example

### Step-by-Step Workflow

```bash
# 1. Set your Keboola credentials
export KEBOOLA_URL="https://connection.keboola.com"  # Your region
export KEBOOLA_TOKEN="1234-567890-abcd..."           # Your token

# 2. Verify connection
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  "$KEBOOLA_URL/v2/storage/tokens/verify"

# 3. Generate data
datagen generate example/bank.json -o output_bank --seed 42

# 4. Export to CSV
datagen export example/bank.json --data-dir output_bank -o output_csv

# 5. Upload to Keboola
python scripts/upload_to_keboola.py output_csv

# Done! Your data is in Keboola
```

---

## Regional Endpoints Reference

### United States

```bash
export KEBOOLA_URL="https://connection.keboola.com"
```

### Europe (Central - Frankfurt)

```bash
export KEBOOLA_URL="https://connection.eu-central-1.keboola.com"
```

### Europe (North - Ireland)

```bash
export KEBOOLA_URL="https://connection.north-europe.azure.keboola.com"
```

### Azure East US

```bash
export KEBOOLA_URL="https://connection.east-us-2.azure.keboola.com"
```

### Not Sure?

The endpoint is **exactly what you see in your browser** when you access Keboola:
- If you visit `https://connection.keboola.com` → use `https://connection.keboola.com`
- If you visit `https://connection.eu-central-1.keboola.com` → use `https://connection.eu-central-1.keboola.com`

---

## Security Best Practices

### ✅ DO:

1. **Store tokens in environment variables**
   ```bash
   export KEBOOLA_TOKEN="your-token"
   ```

2. **Use .env files for local development**
   ```bash
   # .env
   KEBOOLA_TOKEN=your-token
   ```
   And add to `.gitignore`

3. **Use CI/CD secrets for automation**
   - GitHub Actions: Repository Secrets
   - GitLab CI: Variables
   - Jenkins: Credentials

4. **Create token-specific for automation**
   - Description: "Datagen CI/CD"
   - Only Storage permissions
   - Can revoke if compromised

### ❌ DON'T:

1. **Hard-code tokens in scripts**
   ```python
   # ❌ BAD
   token = "1234-567890-abcd..."
   ```

2. **Commit tokens to git**
   - Check `.gitignore` includes `.env`
   - Use `git secrets` or similar tools

3. **Share tokens in plain text**
   - Use password managers
   - Encrypt if sending via email

4. **Use admin tokens for automation**
   - Create limited-scope tokens
   - Principle of least privilege

---

## Troubleshooting

### Issue: "Token not found" or "Unauthorized"

**Cause**: Token is invalid, expired, or wrong

**Solutions**:
1. Generate a new token in Keboola UI
2. Check you copied the entire token
3. Verify token has Storage permissions
4. Check token isn't disabled

### Issue: "Wrong endpoint"

**Cause**: Using wrong regional URL

**Solutions**:
1. Check your login URL
2. Try common endpoints (US, EU)
3. Contact your Keboola admin

### Issue: "Permission denied"

**Cause**: Token doesn't have write permissions

**Solutions**:
1. Go to Settings → API Tokens in Keboola
2. Edit token or create new one
3. Enable Storage → Write permission

### Issue: "Environment variable not set"

**Cause**: Variables not exported

**Solutions**:
```bash
# Check if set
echo $KEBOOLA_TOKEN
echo $KEBOOLA_URL

# Set them
export KEBOOLA_URL="https://connection.keboola.com"
export KEBOOLA_TOKEN="your-token-here"

# Verify
python scripts/upload_to_keboola.py --help
```

---

## Summary

**Required Credentials:**

1. **Endpoint URL**:
   - Where you log in to Keboola
   - Example: `https://connection.keboola.com`

2. **Storage API Token**:
   - Get from: Keboola UI → Settings → API Tokens
   - Needs: Storage read/write permissions

**Setup:**
```bash
export KEBOOLA_URL="your-endpoint-here"
export KEBOOLA_TOKEN="your-token-here"
```

**Test:**
```bash
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  "$KEBOOLA_URL/v2/storage/tokens/verify"
```

**Use:**
```bash
python scripts/upload_to_keboola.py output_csv
```

That's it! 🎉

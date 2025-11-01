# Using .env File for Keboola Credentials

Store your Keboola credentials securely in a `.env` file instead of setting environment variables every time.

---

## Quick Start

### 1. Install python-dotenv

```bash
# Install Keboola dependencies (includes python-dotenv)
pip install -e ".[keboola]"

# Or install individually
pip install python-dotenv kbcstorage
```

### 2. Create .env File

Copy the example file:
```bash
cp .env.example .env
```

Or create manually:
```bash
cat > .env << 'EOF'
# Keboola Connection Credentials
KEBOOLA_URL=https://connection.keboola.com
KEBOOLA_TOKEN=your-token-here
EOF
```

### 3. Edit .env File

Open `.env` in your editor and fill in your credentials:

```bash
# US Region
KEBOOLA_URL=https://connection.keboola.com
KEBOOLA_TOKEN=1234-567890-abcdefghijklmnop...

# EU Region
# KEBOOLA_URL=https://connection.eu-central-1.keboola.com
# KEBOOLA_TOKEN=your-eu-token-here
```

### 4. Run Upload Script

```bash
# No need to export variables - automatically loaded from .env
python scripts/upload_to_keboola.py output_csv
```

**Done!** The script automatically loads credentials from `.env` ✅

---

## .env File Format

### Template

```bash
# Keboola Connection Credentials
# Lines starting with # are comments

# Your Keboola endpoint URL (required)
KEBOOLA_URL=https://connection.keboola.com

# Your Storage API token (required)
KEBOOLA_TOKEN=your-token-here

# Optional: Default bucket name
# KEBOOLA_BUCKET=datagen
```

### Regional Endpoints

```bash
# United States
KEBOOLA_URL=https://connection.keboola.com

# Europe (Central - Frankfurt)
KEBOOLA_URL=https://connection.eu-central-1.keboola.com

# Europe (North - Ireland)
KEBOOLA_URL=https://connection.north-europe.azure.keboola.com

# Azure East US
KEBOOLA_URL=https://connection.east-us-2.azure.keboola.com
```

### Example with Real Token

```bash
KEBOOLA_URL=https://connection.keboola.com
KEBOOLA_TOKEN=1234-567890-abcdefghijklmnopqrstuvwxyz0123456789
```

---

## Security

### ✅ Best Practices

1. **Add .env to .gitignore** (already done)
   ```bash
   # .gitignore already includes:
   .env
   .env.local
   .env.*.local
   ```

2. **Never commit .env to git**
   ```bash
   # Check if .env is ignored
   git check-ignore .env
   # Should output: .env
   ```

3. **Use .env.example for templates**
   ```bash
   # Commit .env.example (without real credentials)
   git add .env.example
   ```

4. **Set proper file permissions**
   ```bash
   # Make .env readable only by you
   chmod 600 .env
   ```

### ❌ Common Mistakes

1. **Committing .env to git**
   ```bash
   # ❌ DON'T DO THIS
   git add .env
   git commit -m "Add credentials"
   ```

2. **Sharing .env file**
   ```bash
   # ❌ DON'T DO THIS
   email .env to someone
   ```

3. **Using production credentials in development**
   ```bash
   # ❌ Use separate tokens for dev/prod
   ```

---

## Multiple Environments

### Development vs Production

Create separate .env files:

```bash
# .env.development
KEBOOLA_URL=https://connection.keboola.com
KEBOOLA_TOKEN=dev-token-here

# .env.production
KEBOOLA_URL=https://connection.keboola.com
KEBOOLA_TOKEN=prod-token-here
```

Load specific environment:

```python
from dotenv import load_dotenv

# Load development
load_dotenv('.env.development')

# Or load production
load_dotenv('.env.production')
```

### Regional Deployments

```bash
# .env.us
KEBOOLA_URL=https://connection.keboola.com
KEBOOLA_TOKEN=us-token

# .env.eu
KEBOOLA_URL=https://connection.eu-central-1.keboola.com
KEBOOLA_TOKEN=eu-token
```

---

## Verification

### Check if .env is Loaded

```bash
# Run upload script - should see message
python scripts/upload_to_keboola.py output_csv

# Expected output:
# 📄 Loaded credentials from .env file
# 📡 Connecting to Keboola...
# ...
```

### Test Credentials

Create a test script `test_credentials.py`:

```python
#!/usr/bin/env python3
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Check variables
url = os.getenv('KEBOOLA_URL')
token = os.getenv('KEBOOLA_TOKEN')

print(f"URL: {url}")
print(f"Token: {token[:10]}..." if token else "Token: Not set")

if url and token:
    print("✅ Credentials loaded successfully")
else:
    print("❌ Missing credentials")
```

Run it:
```bash
python test_credentials.py
```

---

## Troubleshooting

### Issue: "KEBOOLA_TOKEN not set"

**Cause**: `.env` file not found or not loaded

**Solutions**:

1. **Check .env file exists**
   ```bash
   ls -la .env
   # Should show: .env
   ```

2. **Check .env location**
   ```bash
   # Must be in project root or current directory
   pwd
   ls .env
   ```

3. **Check .env content**
   ```bash
   cat .env
   # Should show your KEBOOLA_URL and KEBOOLA_TOKEN
   ```

4. **Install python-dotenv**
   ```bash
   pip install python-dotenv
   ```

### Issue: ".env file not loaded"

**Cause**: Running script from wrong directory

**Solution**:
```bash
# Run from project root
cd /path/to/datagen
python scripts/upload_to_keboola.py output_csv

# Or use absolute path to .env
```

### Issue: "Invalid token"

**Cause**: Wrong token in .env or extra spaces

**Solutions**:

1. **Check for spaces**
   ```bash
   # ❌ Wrong (space after =)
   KEBOOLA_TOKEN= 1234-567890-abc...

   # ✅ Correct (no spaces)
   KEBOOLA_TOKEN=1234-567890-abc...
   ```

2. **Check for quotes** (not needed)
   ```bash
   # ❌ Don't use quotes
   KEBOOLA_TOKEN="1234-567890-abc..."

   # ✅ Just the value
   KEBOOLA_TOKEN=1234-567890-abc...
   ```

3. **Regenerate token**
   - Go to Keboola UI → Settings → API Tokens
   - Create new token
   - Update .env

---

## Advanced Usage

### Load .env Programmatically

```python
from dotenv import load_dotenv
from pathlib import Path

# Load from specific path
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Override existing environment variables
load_dotenv(override=True)

# Load but don't override
load_dotenv(override=False)
```

### Use in Other Scripts

```python
#!/usr/bin/env python3
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Access credentials
url = os.getenv('KEBOOLA_URL')
token = os.getenv('KEBOOLA_TOKEN')
bucket = os.getenv('KEBOOLA_BUCKET', 'datagen')  # Default value

print(f"Connecting to {url}")
# Use credentials...
```

### CI/CD Integration

For GitHub Actions, GitLab CI, etc., use secrets instead of .env:

**GitHub Actions:**
```yaml
# .github/workflows/upload.yml
env:
  KEBOOLA_URL: ${{ secrets.KEBOOLA_URL }}
  KEBOOLA_TOKEN: ${{ secrets.KEBOOLA_TOKEN }}

steps:
  - name: Upload to Keboola
    run: python scripts/upload_to_keboola.py output_csv
```

**GitLab CI:**
```yaml
# .gitlab-ci.yml
upload:
  script:
    - export KEBOOLA_URL=$KEBOOLA_URL
    - export KEBOOLA_TOKEN=$KEBOOLA_TOKEN
    - python scripts/upload_to_keboola.py output_csv
```

---

## Complete Example

### Setup

```bash
# 1. Install dependencies
pip install -e ".[keboola]"

# 2. Create .env file
cp .env.example .env

# 3. Edit .env
nano .env
# Add your KEBOOLA_URL and KEBOOLA_TOKEN

# 4. Verify .env
cat .env | grep -v "^#" | grep -v "^$"
# Should show your URL and token
```

### Usage

```bash
# 1. Generate data
datagen generate example/bank.json -o output --seed 42

# 2. Export to CSV
datagen export example/bank.json --data-dir output -o csv_export

# 3. Upload to Keboola (credentials auto-loaded from .env)
python scripts/upload_to_keboola.py csv_export

# No need to export KEBOOLA_URL or KEBOOLA_TOKEN!
```

### Expected Output

```
📄 Loaded credentials from .env file
📡 Connecting to Keboola...
   ✓ Connected as: Datagen Upload Script
📦 Checking bucket: in.c-datagen
   ✓ Bucket exists

📋 Dataset Information:
   Name: BankSchema
   Version: 1.0
   Tables: 10
   Total Rows: 143,098

🔄 Uploading 10 tables...
  branch... ✓ Created (PK: ['branch_id'])
  customer... ✓ Created (PK: ['customer_id'])
  ...

✅ Upload Summary:
   Uploaded: 10/10 tables
   Bucket: in.c-datagen
```

---

## Summary

**Benefits of .env:**
- ✅ Store credentials once
- ✅ No need to export variables every time
- ✅ Easier to manage multiple environments
- ✅ More secure (if .gitignore is correct)
- ✅ Team-friendly (everyone uses same format)

**Setup:**
```bash
# 1. Install
pip install python-dotenv kbcstorage

# 2. Create .env
cp .env.example .env

# 3. Edit .env with your credentials

# 4. Run (auto-loads from .env)
python scripts/upload_to_keboola.py output_csv
```

**Security Checklist:**
- ✅ .env is in .gitignore
- ✅ Never commit .env
- ✅ File permissions set to 600
- ✅ Use .env.example for templates
- ✅ Separate tokens for dev/prod

That's it! Your credentials are now securely stored in `.env` 🔒

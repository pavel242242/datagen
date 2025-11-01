# Datagen → Keboola Connection

**Upload synthetic data to Keboola in 3 steps**

---

## 📋 What You Need

Before uploading to Keboola, you need **2 credentials**:

```
┌─────────────────────────────────────────────────┐
│  1. ENDPOINT URL                                │
│     Where you access Keboola                    │
│                                                 │
│     Examples:                                   │
│     • https://connection.keboola.com (US)       │
│     • https://connection.eu-central-1...  (EU)  │
│                                                 │
│     → Use the URL you log in with              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  2. STORAGE API TOKEN                           │
│     Authentication token                        │
│                                                 │
│     Get from:                                   │
│     Keboola UI → Settings → API Tokens          │
│                                                 │
│     Permissions needed:                         │
│     ✓ Storage → Read                            │
│     ✓ Storage → Write                           │
│                                                 │
│     Example: 1234-567890-abcdefg...             │
└─────────────────────────────────────────────────┘
```

**📖 Detailed Instructions**: See [`KEBOOLA_CREDENTIALS.md`](KEBOOLA_CREDENTIALS.md)

---

## 🚀 Quick Start

### Step 1: Generate Data

```bash
datagen generate example/bank.json -o output --seed 42
datagen export example/bank.json --data-dir output -o csv_export
```

### Step 2: Set Credentials

**Option A: .env File (Recommended)**

```bash
# Install dependencies
pip install -e ".[keboola]"

# Create .env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Your `.env` file:
```bash
KEBOOLA_URL=https://connection.keboola.com
KEBOOLA_TOKEN=your-token-here
```

**Option B: Environment Variables**

```bash
export KEBOOLA_URL="https://connection.keboola.com"
export KEBOOLA_TOKEN="your-token-here"
```

### Step 3: Upload

```bash
# Upload to Keboola (credentials auto-loaded from .env)
python scripts/upload_to_keboola.py csv_export
```

**Done!** Your data is now in Keboola Connection 🎉

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **KEBOOLA_CREDENTIALS.md** | How to get endpoint & token (detailed) |
| **QUICK_START_KEBOOLA.md** | Quick reference card |
| **KEBOOLA_UPLOAD.md** | Complete upload guide (5 methods) |
| **EXPORT_GUIDE.md** | CSV export documentation |

---

## ❓ Common Questions

### Q: Which endpoint do I use?

**A:** Use the URL you see when you log in to Keboola.

- If you visit `connection.keboola.com` → use `https://connection.keboola.com`
- If you visit `connection.eu-central-1.keboola.com` → use `https://connection.eu-central-1.keboola.com`

### Q: Where do I get the Storage API token?

**A:** In Keboola UI:
1. Settings (gear icon)
2. API Tokens
3. New Token
4. Enable Storage read/write
5. Copy token

**See detailed guide**: [`KEBOOLA_CREDENTIALS.md`](KEBOOLA_CREDENTIALS.md)

### Q: Do I need both endpoint and token?

**A:** Yes! Both are required:
- **Endpoint** = Where to connect (your Keboola region)
- **Token** = Authentication (like a password)

### Q: Can I hardcode the credentials?

**A:** No! Use environment variables:
```bash
export KEBOOLA_URL="https://connection.keboola.com"
export KEBOOLA_TOKEN="your-token"
```

Never commit tokens to git!

### Q: How do I verify my credentials?

**A:** Test with curl:
```bash
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  "$KEBOOLA_URL/v2/storage/tokens/verify"
```

Should return your token info (not an error).

---

## 🔒 Security Notes

✅ **DO**:
- Store tokens in environment variables
- Use `.env` files (add to `.gitignore`)
- Use CI/CD secrets for automation
- Create separate tokens for different purposes

❌ **DON'T**:
- Hardcode tokens in scripts
- Commit tokens to git
- Share tokens in plain text
- Use admin tokens for automation

---

## 🛠️ Troubleshooting

### "KEBOOLA_TOKEN not set"

```bash
# Check if set
echo $KEBOOLA_TOKEN

# Set it
export KEBOOLA_URL="https://connection.keboola.com"
export KEBOOLA_TOKEN="your-token-here"
```

### "401 Unauthorized"

- Token is invalid or expired
- Generate a new token in Keboola UI

### "403 Forbidden"

- Token doesn't have Storage permissions
- Edit token to enable Storage read/write

### "Connection refused"

- Wrong endpoint URL
- Check your Keboola login URL

---

## 📖 Full Example

```bash
# 1. Set credentials (REQUIRED)
export KEBOOLA_URL="https://connection.keboola.com"
export KEBOOLA_TOKEN="1234-567890-abcdefg..."

# 2. Verify connection
curl -H "X-StorageApi-Token: $KEBOOLA_TOKEN" \
  "$KEBOOLA_URL/v2/storage/tokens/verify"

# 3. Generate data
datagen generate example/bank.json -o output_bank --seed 42

# 4. Export to CSV
datagen export example/bank.json --data-dir output_bank -o csv_export

# 5. Upload to Keboola
pip install kbcstorage
python scripts/upload_to_keboola.py csv_export

# 6. Check in Keboola UI
# Go to: Storage → Tables → in.c-datagen
```

---

## 🎯 Next Steps

1. **Get your credentials** → See [`KEBOOLA_CREDENTIALS.md`](KEBOOLA_CREDENTIALS.md)
2. **Run quick test** → Follow Quick Start above
3. **Read full guide** → See [`KEBOOLA_UPLOAD.md`](KEBOOLA_UPLOAD.md)
4. **Automate uploads** → Add to CI/CD pipeline

---

## 📞 Support

- **Credentials help**: See [`KEBOOLA_CREDENTIALS.md`](KEBOOLA_CREDENTIALS.md)
- **Upload methods**: See [`KEBOOLA_UPLOAD.md`](KEBOOLA_UPLOAD.md)
- **Keboola docs**: https://help.keboola.com/
- **Python client**: https://github.com/keboola/python-storage-api-client

---

**Remember**: You need both the **endpoint URL** and **Storage API token** to upload! 🔑

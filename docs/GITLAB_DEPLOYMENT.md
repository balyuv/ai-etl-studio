# GitLab Deployment Guide

## Test Database Setup for GitLab

### Overview

The test database credentials are now stored in the `.config/` directory and can be committed to GitLab. This allows all users who clone the repository to have immediate access to the test database.

## File Locations

```
nl_to_sql_convertor/
├── .config/                    # ✅ COMMITTED to GitLab
│   ├── test_db.enc            # Encrypted test DB credentials
│   ├── test_db.key            # Encryption key
│   └── README.md              # Documentation
├── .env                        # ❌ NOT committed (in .gitignore)
└── ~/.asksql_credentials.json  # ❌ NOT committed (user's home dir)
```

## Step-by-Step: Committing Test Database to GitLab

### 1. Configure Test Database Locally

```bash
# Run the app
cd /Users/by/AI_ETL_Studio/nl_to_sql_convertor
.venv/bin/streamlit run app.py
```

Then in the UI:
1. Select "🧪 Test Database" mode
2. Fill in your test database credentials
3. Click "💾 Save Test Database"

### 2. Verify Files Were Created

```bash
ls -la .config/
# Should show:
# test_db.enc
# test_db.key
# README.md
```

### 3. Commit to GitLab

```bash
# Add the config directory
git add .config/

# Commit with a descriptive message
git commit -m "Add encrypted test database credentials for demo/testing"

# Push to GitLab
git push origin main
```

### 4. Verify on GitLab

Visit your GitLab repository and confirm the `.config/` directory is visible with all files.

## For Team Members Cloning the Repo

When someone clones your repository:

```bash
git clone <your-gitlab-repo-url>
cd nl_to_sql_convertor

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

They can immediately:
1. Select "🧪 Test Database" in the sidebar
2. Get connected automatically
3. Start querying!

## Security Considerations

### ✅ Safe to Commit

- `.config/test_db.enc` - Encrypted credentials
- `.config/test_db.key` - Encryption key
- **Why?** These are for a test database with sample data only

### ❌ Never Commit

- `.env` - Contains OpenAI API key and production secrets
- Personal database credentials (stored in home directory)
- Any production database credentials

## Environment Variables

Make sure each deployment has a `.env` file with:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

This file is in `.gitignore` and must be set up separately on each deployment.

## CI/CD Pipeline (Optional)

If you're using GitLab CI/CD, add this to `.gitlab-ci.yml`:

```yaml
test:
  stage: test
  script:
    - pip install -r requirements.txt
    - echo "OPENAI_API_KEY=$OPENAI_API_KEY" > .env
    - streamlit run app.py --server.headless true &
    - sleep 10
    - curl http://localhost:8501
  only:
    - main
```

## Updating Test Database Credentials

To update the test database credentials:

```bash
# 1. Update through the UI (Admin section)
# 2. Commit the changes
git add .config/
git commit -m "Update test database credentials"
git push origin main

# 3. Team members pull the changes
git pull origin main
```

## Troubleshooting

### Issue: Test database not appearing after clone

**Solution**: Make sure the `.config/` directory was committed:
```bash
git ls-files .config/
# Should show all files in .config/
```

### Issue: Permission denied when connecting

**Solution**: Verify the test database credentials are correct and the database is accessible from your network.

### Issue: Encryption/decryption error

**Solution**: Delete and reconfigure:
```bash
rm -rf .config/
# Reconfigure through UI
git add .config/
git commit -m "Reconfigure test database"
git push
```

## Best Practices

1. **Use a cloud-hosted test database** - Makes it accessible from anywhere
2. **Read-only permissions** - Test database user should only have SELECT
3. **Sample data** - Use realistic but non-sensitive data
4. **Document the schema** - Keep README updated with available tables
5. **Regular rotation** - Update credentials periodically

## Example: Cloud Test Database Setup

### Option 1: Railway.app (Free PostgreSQL)
1. Sign up at railway.app
2. Create a new PostgreSQL database
3. Copy the connection details
4. Configure in the app

### Option 2: PlanetScale (Free MySQL)
1. Sign up at planetscale.com
2. Create a new database
3. Create a read-only user
4. Configure in the app

### Option 3: Supabase (Free PostgreSQL)
1. Sign up at supabase.com
2. Create a new project
3. Use the provided connection string
4. Configure in the app

---

**Ready to deploy!** 🚀

Your test database credentials are now safely encrypted and ready to be shared via GitLab.

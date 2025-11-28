# Test Database Configuration

This directory contains the encrypted test database credentials that are shared across all deployments.

## Files

- **`test_db.enc`** - Encrypted test database credentials (safe to commit)
- **`test_db.key`** - Encryption key for the test database (safe to commit)

## Security Note

⚠️ **These files are INTENTIONALLY committed to the repository.**

This is safe because:
1. ✅ The credentials are for a **test/demo database only**
2. ✅ The test database should contain **non-sensitive sample data**
3. ✅ The test database user should have **read-only permissions**
4. ✅ The credentials are **encrypted** using Fernet encryption

## Setup

When you clone this repository:

1. If these files exist, the test database will be automatically available
2. Users can select "🧪 Test Database" and connect immediately
3. No additional setup required!

## Admin: Configuring Test Database

To set up or update the test database credentials:

1. Run the application: `streamlit run app.py`
2. Select "🧪 Test Database" mode in the sidebar
3. Fill in the test database configuration form
4. Click "💾 Save Test Database"
5. Commit the `.config/` directory to GitLab:
   ```bash
   git add .config/
   git commit -m "Update test database credentials"
   git push
   ```

## Best Practices

1. **Use a dedicated test database** - Don't use production data
2. **Read-only user** - Create a database user with SELECT-only permissions
3. **Sample data** - Populate with realistic but non-sensitive data
4. **Regular updates** - Update credentials periodically for security
5. **Document the schema** - Keep track of what tables/data are available

## Example Test Database User Setup

### MySQL
```sql
CREATE USER 'test_user'@'%' IDENTIFIED BY 'secure_password';
GRANT SELECT ON sample_db.* TO 'test_user'@'%';
FLUSH PRIVILEGES;
```

### PostgreSQL
```sql
CREATE USER test_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE sample_db TO test_user;
GRANT USAGE ON SCHEMA public TO test_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO test_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO test_user;
```

## Troubleshooting

### Files not appearing after git clone?

Make sure the files were committed:
```bash
git add .config/
git commit -m "Add test database credentials"
git push
```

### Need to reset the test database?

Delete the files and reconfigure:
```bash
rm -rf .config/
# Then reconfigure through the UI
```

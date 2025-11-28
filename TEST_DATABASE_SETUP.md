# Test Database Feature

## Overview

The application now includes a **Test Database** feature that allows users to quickly connect to a pre-configured database without entering their own credentials. This is perfect for:

- **Demo purposes** - Show the app to others without sharing your database credentials
- **Testing** - Try out the app before connecting to your own database
- **Onboarding** - Help new users get started quickly

## Security

Test database credentials are stored with **Fernet encryption** (symmetric encryption from the `cryptography` library), providing strong security for the stored credentials.

### Storage Locations

The encrypted credentials are stored in your home directory:
- **Encryption Key**: `~/.asksql_key.key` (auto-generated)
- **Encrypted Credentials**: `~/.asksql_test_db.enc`

⚠️ **Important**: Keep the `.asksql_key.key` file secure. Anyone with access to both the key and encrypted file can decrypt the credentials.

## How to Use

### For Users

1. Open the application
2. In the sidebar, select **"🧪 Test Database"** from the Connection Mode options
3. If configured, you'll be automatically connected to the test database
4. Start querying!

### For Administrators

#### Initial Setup

1. Select **"🧪 Test Database"** mode
2. Fill in the test database configuration form:
   - Database Type (PostgreSQL or MySQL)
   - Host
   - Port
   - User
   - Password
   - Database Name
   - Schema (PostgreSQL only)
3. Click **"💾 Save Test Database"**
4. The credentials are encrypted and saved

#### Updating Test Database

1. Select **"🧪 Test Database"** mode
2. Expand the **"🔧 Admin: Reconfigure Test Database"** section
3. Update the credentials as needed
4. Click **"💾 Update Test Database"**

## Technical Details

### Encryption Method

- **Algorithm**: Fernet (symmetric encryption)
- **Library**: `cryptography` (Python)
- **Key Generation**: Automatic on first use
- **Key Storage**: `~/.asksql_key.key`

### Functions

- `get_or_create_encryption_key()` - Manages the encryption key
- `save_test_db_credentials(config)` - Encrypts and saves credentials
- `load_test_db_credentials()` - Decrypts and loads credentials

## Comparison: Test Database vs My Database

| Feature | Test Database | My Database |
|---------|--------------|-------------|
| **Setup** | One-time admin setup | Each user enters credentials |
| **Security** | Fernet encryption | Base64 encoding (optional) |
| **Use Case** | Demos, testing, onboarding | Production use |
| **Credentials** | Shared (encrypted) | Personal |
| **Remember Me** | Always on | Optional |

## Best Practices

1. **Use for demos only** - Don't use production databases as test databases
2. **Secure the key file** - Protect `~/.asksql_key.key` with appropriate file permissions
3. **Regular updates** - Update test database credentials periodically
4. **Limited access** - Use a database user with read-only permissions for the test database
5. **Sample data** - Populate the test database with non-sensitive sample data

## Troubleshooting

### "Test database not configured" message

**Solution**: An admin needs to set up the test database credentials using the configuration form.

### Cannot decrypt credentials

**Possible causes**:
- Encryption key file is missing or corrupted
- Encrypted credentials file is corrupted

**Solution**: Delete both files and reconfigure:
```bash
rm ~/.asksql_key.key
rm ~/.asksql_test_db.enc
```

### Connection fails

**Solution**: Verify the test database credentials are correct by trying to connect manually, then update the configuration.

## Example Test Database Setup

Here's an example configuration for a local MySQL test database:

```
Database Type: MySQL
Host: localhost
Port: 3306
User: test_user
Password: [secure_password]
Database Name: sample_ecommerce
```

This allows users to immediately start querying sample e-commerce data without any setup!

import os
import json
import base64
from pathlib import Path
import pandas as pd
import streamlit as st
import psycopg2
import mysql.connector
from cryptography.fernet import Fernet

# 💾 Credential persistence helpers
# Personal credentials stored in home directory (not committed to git)
CREDS_FILE = Path.home() / ".asksql_credentials.json"

# Test database credentials stored in project directory (can be committed to git)
PROJECT_DIR = Path(__file__).parent
CONFIG_DIR = PROJECT_DIR / ".config"
TEST_DB_FILE = CONFIG_DIR / "test_db.enc"
ENCRYPTION_KEY_FILE = CONFIG_DIR / "test_db.key"

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True)

def get_or_create_encryption_key():
    """Get or create encryption key for test database credentials"""
    try:
        if ENCRYPTION_KEY_FILE.exists():
            with open(ENCRYPTION_KEY_FILE, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(ENCRYPTION_KEY_FILE, 'wb') as f:
                f.write(key)
            return key
    except Exception as e:
        st.error(f"Failed to manage encryption key: {e}")
        return None

def save_test_db_credentials(config):
    """Save test database credentials with encryption"""
    try:
        key = get_or_create_encryption_key()
        if not key:
            return False
        
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(json.dumps(config).encode())
        
        with open(TEST_DB_FILE, 'wb') as f:
            f.write(encrypted_data)
        return True
    except Exception as e:
        st.error(f"Failed to save test database credentials: {e}")
        return False

def load_test_db_credentials():
    """Load encrypted test database credentials"""
    try:
        if not TEST_DB_FILE.exists():
            return None
        
        key = get_or_create_encryption_key()
        if not key:
            return None
        
        fernet = Fernet(key)
        with open(TEST_DB_FILE, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    except Exception as e:
        return None

def credentials_exist():
    return CREDS_FILE.exists()

def save_credentials(config):
    """Save credentials to local file (base64 encoded for basic obfuscation)"""
    try:
        # Encode password for basic obfuscation (NOT encryption, just prevents plain text)
        config_copy = config.copy()
        if config_copy.get('password'):
            config_copy['password'] = base64.b64encode(config_copy['password'].encode()).decode()
        
        with open(CREDS_FILE, 'w') as f:
            json.dump(config_copy, f)
        return True
    except Exception as e:
        st.error(f"Failed to save credentials: {e}")
        return False

def load_credentials():
    """Load credentials from local file"""
    try:
        if CREDS_FILE.exists():
            with open(CREDS_FILE, 'r') as f:
                config = json.load(f)
            # Decode password
            if config.get('password'):
                config['password'] = base64.b64decode(config['password'].encode()).decode()
            return config
        return {}
    except Exception as e:
        return {}

def clear_saved_credentials():
    """Delete saved credentials file"""
    try:
        if CREDS_FILE.exists():
            CREDS_FILE.unlink()
        return True
    except Exception:
        return False

@st.cache_resource(ttl=300, show_spinner=True)
def get_schema(db_type, host, port, user, password, dbname, schema):
    try:
        if db_type == "PostgreSQL":
            conn = psycopg2.connect(host=host, port=port, user=user, password=password, database=dbname)
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = %s AND table_type='BASE TABLE'
                ORDER BY table_name
            """, (schema,))
            tables = [r[0] for r in cur.fetchall()]
            
            schema_dict = {}
            for t in tables:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema=%s AND table_name=%s
                    ORDER BY ordinal_position
                """, (schema, t))
                schema_dict[t] = [c[0] for c in cur.fetchall()]
            cur.close()
            conn.close()
            return schema_dict
            
        elif db_type == "MySQL":
            conn = mysql.connector.connect(host=host, port=port, user=user, password=password, database=dbname)
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            tables = [r[0] for r in cur.fetchall()]
            
            schema_dict = {}
            for t in tables:
                cur.execute(f"DESCRIBE `{t}`")
                schema_dict[t] = [r[0] for r in cur.fetchall()]
            cur.close()
            conn.close()
            return schema_dict
            
    except Exception as e:
        return {"_error": str(e)}

def run_query(db_type, host, port, user, password, dbname, sql):
    try:
        if db_type == "PostgreSQL":
            conn = psycopg2.connect(host=host, port=port, user=user, password=password, database=dbname)
        elif db_type == "MySQL":
            conn = mysql.connector.connect(host=host, port=port, user=user, password=password, database=dbname)
            
        df = pd.read_sql(sql, conn)
        conn.close()
        
        # Fix duplicate column names if they exist
        cols = pd.Series(df.columns)
        if cols.duplicated().any():
            # Add suffix to duplicate column names
            for dup in cols[cols.duplicated()].unique():
                dup_indices = [i for i, x in enumerate(cols) if x == dup]
                for i, idx in enumerate(dup_indices):
                    cols[idx] = f"{dup}_{i+1}"
            df.columns = cols
            st.warning(f"⚠️ Duplicate column names detected and renamed. Original query had duplicate columns.")
        
        return df
    except Exception as e:
        st.error(f"❌ SQL Execution Failed: {e}")
        return pd.DataFrame()

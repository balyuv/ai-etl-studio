import json
import mysql.connector
from mysql.connector import Error

# Load config
with open("db_config.json", "r") as f:
    cfg = json.load(f)

print("Testing database connection...")
print(f"Host: {cfg['host']}")
print(f"User: {cfg['user']}")
print(f"Database: {cfg['database']}")
print()

try:
    conn = mysql.connector.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        connect_timeout=5
    )
    print("✅ Connection successful!")
    
    cur = conn.cursor()
    cur.execute("SHOW TABLES;")
    tables = [row[0] for row in cur.fetchall()]
    
    print(f"✅ Found {len(tables)} tables:")
    for t in tables:
        print(f"  - {t}")
    
    cur.close()
    conn.close()
    
except Error as e:
    print(f"❌ Connection failed: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

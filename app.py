import os
import json
import re
import base64
from pathlib import Path
import pandas as pd
import streamlit as st
import psycopg2
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# ⚡ Page config must be first
st.set_page_config(
    page_title="AskSQL – Natural Language to SQL",
    page_icon="⚡",
    layout="wide"
)

# 🔑 Load environment variables
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    st.error("❌ Missing OpenAI API Key")
    st.stop()

client = OpenAI(api_key=OPENAI_KEY)

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

# 🎨 Premium UI Design System
with st.sidebar:
    st.write("")
    dark_mode = st.toggle("🌗 Dark Mode", value=True)

if dark_mode:
    # Vibrant dark theme with dramatic effects
    ROOT_BG = "linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%)"
    ROOT_BG_SOLID = "#0a0e27"
    ROOT_TEXT = "#ffffff"
    CARD_BG = "rgba(40, 48, 75, 0.75)"  # Lighter blue-gray for better visibility
    INPUT_BG = "rgba(255, 255, 255, 0.08)" # Light overlay for inputs
    CARD_BORDER = "rgba(88, 166, 255, 0.3)"
    ACCENT = "#00d4ff"
    ACCENT_HOVER = "#00f0ff"
    SECONDARY = "#ffffff" # Pure white for maximum visibility
    SUCCESS = "#00ff88"
    SHADOW = "0 20px 60px rgba(0, 0, 0, 0.6)"
    GLOW = "0 0 40px rgba(0, 212, 255, 0.5)"
    GRADIENT_PRIMARY = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    GRADIENT_ACCENT = "linear-gradient(135deg, #00d4ff 0%, #0099ff 100%)"
    EXPANDER_ARROW = "#00d4ff"  # Cyan for dark mode
else:
    # Vibrant light theme with dramatic effects
    ROOT_BG = "linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 50%, #f8f9ff 100%)"
    ROOT_BG_SOLID = "#ffffff"
    ROOT_TEXT = "#1a202c"
    CARD_BG = "rgba(255, 255, 255, 0.85)"
    INPUT_BG = "rgba(255, 255, 255, 0.9)"
    CARD_BORDER = "rgba(102, 126, 234, 0.25)"
    ACCENT = "#667eea"
    ACCENT_HOVER = "#5568d3"
    SECONDARY = "#718096"
    SUCCESS = "#48bb78"
    SHADOW = "0 20px 60px rgba(102, 126, 234, 0.25)"
    GLOW = "0 0 40px rgba(102, 126, 234, 0.4)"
    GRADIENT_PRIMARY = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    GRADIENT_ACCENT = "linear-gradient(135deg, #667eea 0%, #0099ff 100%)"
    EXPANDER_ARROW = "#FFB800"  # Bright yellow for light mode

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


# 🔌 Sidebar Database Connection
with st.sidebar:
    # Professional Header
    st.markdown(f"""
    <div style="
        padding: 20px 0 16px 0;
        border-bottom: 2px solid {CARD_BORDER if 'CARD_BORDER' in dir() else '#e0e0e0'};
        margin-bottom: 20px;
    ">
        <div style="
            font-size: 1.1rem;
            font-weight: 700;
            color: {ACCENT if 'ACCENT' in dir() else '#667eea'};
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        ">
            <span style="font-size: 1.3rem;">🔌</span>
            <span>Connection Manager</span>
        </div>
        <div style="
            font-size: 0.85rem;
            color: {SECONDARY if 'SECONDARY' in dir() else '#718096'};
            font-weight: 400;
        ">
            Configure your database connection
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Connection Mode Selector with better styling
    st.markdown(f"""
    <div style="
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 12px;
        color: {SECONDARY};
    ">
        CONNECTION TYPE
    </div>
    """, unsafe_allow_html=True)
    
    connection_mode = st.radio(
        "Connection Mode",
        ["🔐 My Database", "🧪 Test Database"],
        help="Choose to connect to your own database or use the test database",
        label_visibility="collapsed"
    )
    
    if connection_mode == "🧪 Test Database":
        # Try to load test database credentials
        test_db_config = load_test_db_credentials()
        
        if test_db_config:
            # Test database is configured
            st.session_state['db_config'] = test_db_config
            st.success("✅ Connected to Test Database")
            st.info(f"**Type:** {test_db_config['type']}\\n\\n**Host:** {test_db_config['host']}")
            
            # Admin option to reconfigure test database
            with st.expander("🔧 Admin: Reconfigure Test Database"):
                st.caption("⚠️ This will update the test database credentials for all users")
                with st.form("test_db_reconfig_form"):
                    test_db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="reconfig_type")
                    test_db_host = st.text_input("Host", value=test_db_config.get("host", ""), key="reconfig_host")
                    test_db_port = st.text_input("Port", value=str(test_db_config.get("port", "")), key="reconfig_port")
                    test_db_user = st.text_input("User", value=test_db_config.get("user", ""), key="reconfig_user")
                    test_db_pass = st.text_input("Password", type="password", key="reconfig_pass")
                    test_db_name = st.text_input("Database Name", value=test_db_config.get("database", ""), key="reconfig_name")
                    
                    if test_db_type == "PostgreSQL":
                        test_db_schema = st.text_input("Schema", value=test_db_config.get("schema", "public"), key="reconfig_schema")
                    else:
                        test_db_schema = None
                    
                    if st.form_submit_button("💾 Update Test Database", use_container_width=True):
                        new_config = {
                            "type": test_db_type,
                            "host": test_db_host,
                            "port": test_db_port,
                            "user": test_db_user,
                            "password": test_db_pass,
                            "database": test_db_name,
                            "schema": test_db_schema
                        }
                        if save_test_db_credentials(new_config):
                            st.session_state['db_config'] = new_config
                            st.success("✅ Test database updated!")
        else:
            # Test database not configured - show setup form
            st.warning("⚠️ Test database not configured")
            st.caption("Admin: Set up the test database credentials below")
            
            with st.form("test_db_initial_setup_form"):
                st.caption("Configure Test Database (Encrypted Storage)")
                test_db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="initial_type")
                test_db_host = st.text_input("Host", value="localhost", key="initial_host")
                test_db_port = st.text_input("Port", value="5432" if test_db_type == "PostgreSQL" else "3306", key="initial_port")
                test_db_user = st.text_input("User", value="postgres" if test_db_type == "PostgreSQL" else "root", key="initial_user")
                test_db_pass = st.text_input("Password", type="password", key="initial_pass")
                test_db_name = st.text_input("Database Name", key="initial_name")
                
                if test_db_type == "PostgreSQL":
                    test_db_schema = st.text_input("Schema", value="public", key="initial_schema")
                else:
                    test_db_schema = None
                
                if st.form_submit_button("💾 Save Test Database", use_container_width=True):
                    config = {
                        "type": test_db_type,
                        "host": test_db_host,
                        "port": test_db_port,
                        "user": test_db_user,
                        "password": test_db_pass,
                        "database": test_db_name,
                        "schema": test_db_schema
                    }
                    if save_test_db_credentials(config):
                        st.session_state['db_config'] = config
                        st.success("✅ Test database configured!")

    
    else:  # My Database mode
        # Load saved credentials from file if not in session
        if 'db_config' not in st.session_state:
            loaded_config = load_credentials()
            if loaded_config:
                st.session_state['db_config'] = loaded_config
                st.session_state['remember_me'] = True
        
        # Get saved values from session state if they exist
        saved_config = st.session_state.get('db_config', {})
        
        # Professional connection form
        st.markdown(f"""
        <div style="
            font-size: 0.9rem;
            font-weight: 600;
            margin: 24px 0 16px 0;
            color: {SECONDARY};
            border-bottom: 1px solid {CARD_BORDER};
            padding-bottom: 8px;
        ">
            📊 DATABASE SETTINGS
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("db_creds"):
            # Database Type
            db_type = st.selectbox(
                "🗄️ Database Type", 
                ["PostgreSQL", "MySQL"],
                index=0 if saved_config.get("type") == "PostgreSQL" else (1 if saved_config.get("type") == "MySQL" else 0)
            )
            
            st.markdown(f"<div style='margin: 16px 0 8px 0; font-size: 0.85rem; font-weight: 600; color: {SECONDARY};'>CONNECTION DETAILS</div>", unsafe_allow_html=True)
            
            # Server Details
            col1, col2 = st.columns([2, 1])
            with col1:
                db_host = st.text_input(
                    "🌐 Server / Host", 
                    value=saved_config.get("host", "localhost"),
                    placeholder="e.g., localhost or db.example.com",
                    key="host_input"
                )
            with col2:
                db_port = st.text_input(
                    "🔌 Port", 
                    value=str(saved_config.get("port", "5432" if db_type == "PostgreSQL" else "3306")),
                    placeholder="5432",
                    key="port_input"
                )
            
            # Database Name
            db_name = st.text_input(
                "💾 Database Name", 
                value=saved_config.get("database", "postgres" if db_type == "PostgreSQL" else ""),
                placeholder="Enter database name",
                key="db_input"
            )
            
            # Schema (PostgreSQL only)
            if db_type == "PostgreSQL":
                db_schema = st.text_input(
                    "📁 Schema", 
                    value=saved_config.get("schema", "public"),
                    placeholder="public",
                    key="schema_input"
                )
            else:
                db_schema = None
            
            st.markdown(f"<div style='margin: 16px 0 8px 0; font-size: 0.85rem; font-weight: 600; color: {SECONDARY};'>AUTHENTICATION</div>", unsafe_allow_html=True)
            
            # Credentials
            db_user = st.text_input(
                "👤 Username", 
                value=saved_config.get("user", "postgres" if db_type == "PostgreSQL" else "root"),
                placeholder="Enter username",
                key="user_input"
            )
            db_pass = st.text_input(
                "🔑 Password", 
                type="password",
                value=saved_config.get("password", ""),
                placeholder="Enter password",
                key="pass_input"
            )
            
            # Remember Me
            st.markdown("<div style='margin: 16px 0 8px 0;'></div>", unsafe_allow_html=True)
            remember_me = st.checkbox(
                "💾 Remember credentials on this computer",
                value=st.session_state.get('remember_me', False),
                help="Saves credentials to ~/.asksql_credentials.json (base64 encoded)"
            )
            
            st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)
                
            col1, col2 = st.columns(2)
            with col1:
                connect_btn = st.form_submit_button("✅ Connect", type="primary", use_container_width=True)
            with col2:
                clear_btn = st.form_submit_button("🗑️ Clear", use_container_width=True)
        
        if connect_btn:
            # Save to session state
            st.session_state['db_config'] = {
                "type": db_type,
                "host": db_host, "port": db_port, "user": db_user, 
                "password": db_pass, "database": db_name, "schema": db_schema
            }
            st.session_state['remember_me'] = remember_me
            
            # Save to file if Remember Me is checked
            if remember_me:
                if save_credentials(st.session_state['db_config']):
                    st.success("✅ Connected & credentials saved!")
                else:
                    st.success("✅ Connected!")
            else:
                # Clear saved file if Remember Me is unchecked
                clear_saved_credentials()
                st.success("✅ Connected!")
            
            st.rerun()
        
        if clear_btn:
            # Clear session state
            if 'db_config' in st.session_state:
                del st.session_state['db_config']
            if 'remember_me' in st.session_state:
                del st.session_state['remember_me']
            
            # Clear saved file
            clear_saved_credentials()
            st.info("🗑️ Credentials cleared!")
            st.rerun()
    
    
    # Professional Connection Status (outside both modes)
    if 'db_config' in st.session_state:
        cfg = st.session_state['db_config']
        
        st.markdown(f"""
        <div style="
            margin-top: 32px;
            padding-top: 20px;
            border-top: 2px solid {CARD_BORDER};
        ">
            <div style="
                font-size: 0.85rem;
                font-weight: 600;
                color: {SECONDARY};
                margin-bottom: 12px;
            ">
                CONNECTION STATUS
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Status indicator
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(72, 187, 120, 0.3);
        ">
            <div style="
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 8px;
            ">
                <span style="
                    font-size: 1.2rem;
                ">✅</span>
                <span style="
                    color: white;
                    font-weight: 700;
                    font-size: 0.95rem;
                ">Connected</span>
            </div>
            <div style="
                color: rgba(255, 255, 255, 0.95);
                font-size: 0.85rem;
                line-height: 1.6;
            ">
                <div style="margin-bottom: 4px;">
                    <strong>Type:</strong> {cfg['type']}
                </div>
                <div style="margin-bottom: 4px;">
                    <strong>Server:</strong> {cfg['host']}:{cfg['port']}
                </div>
                <div>
                    <strong>Database:</strong> {cfg.get('database', 'N/A')}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show if credentials are saved
        if CREDS_FILE.exists():
            st.markdown("""
            <div style="
                font-size: 0.8rem;
                color: #718096;
                text-align: center;
                padding: 8px;
                background: rgba(102, 126, 234, 0.1);
                border-radius: 8px;
            ">
                💾 Credentials saved locally
            </div>
            """, unsafe_allow_html=True)



if 'db_config' not in st.session_state:
    st.info("👈 Please enter your database credentials or use the Test Database in the sidebar to get started.")
    st.stop()

# Load config from session state
DB_TYPE = st.session_state['db_config']['type']
DB_HOST = st.session_state['db_config']['host']
DB_PORT = int(st.session_state['db_config']['port'])
DB_USER = st.session_state['db_config']['user']
DB_PASS = st.session_state['db_config']['password']
DB_NAME = st.session_state['db_config']['database']
DB_SCHEMA = st.session_state['db_config']['schema'] if st.session_state['db_config']['schema'] else 'public'

# 🔍 Safe Schema Discovery
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

schema_objects = get_schema(DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, DB_SCHEMA)

if "_error" in schema_objects:
    schema_objects = {}
    TABLES = []
    STATUS = False
else:
    TABLES = list(schema_objects.keys())
    STATUS = True

# 🧠 NL → SQL generation
def generate_sql(nl_text: str) -> str:
    if not STATUS:
        return "SELECT 'Schema unavailable' AS error_message LIMIT 100"

    schema_desc = "\n".join(f'TABLE "{t}" (columns: {", ".join(schema_objects[t])})' for t in TABLES)
    
    if DB_TYPE == "MySQL":
        system_prompt = f"""You are AskSQL, a MySQL expert.


    Database Schema:
    {schema_desc}
    
    Rules:
    1. Build ONE valid MySQL SELECT query.
    2. Use ONLY tables and columns from the schema above.
    3. Do NOT use schema/database prefixes.
    4. Do NOT query system tables.
    5. Always include LIMIT 1000. No semicolons.
    
    CRITICAL SQL CONSTRAINTS:
    6. **NO CTEs (WITH ... AS)**: Your MySQL version does not support them. Use nested subqueries only.
    7. **NO WINDOW FUNCTIONS**: Your MySQL version does NOT support `OVER()`, `NTILE()`, `ROW_NUMBER()`, `RANK()`. Do NOT use them.
       - WRONG: `ROW_NUMBER() OVER (PARTITION BY ...)`
       - WRONG: `RANK() OVER (...)`
       - RIGHT: Use standard `GROUP BY`, `ORDER BY`, and `LIMIT`.
    8. **NO PERCENTILE functions**: Use subqueries with ORDER BY and LIMIT.
    9. **STRICT ALIASING**: Always use short, unique table aliases (e.g., `s` for sales, `st` for store, `cust` for customer, `cat` for category). NEVER use the same alias for different tables.
    10. **NO DUPLICATE COLUMNS**: When joining, if a column exists in multiple tables, select it from ONE table only or alias it.
    11. **DEFINE ALIASES BEFORE USE**: Ensure every alias used in SELECT/WHERE/GROUP BY is actually defined in the FROM/JOIN clause. For example, do not use `reg.region` if `reg` is not a table alias. Use `st.region` instead.

    CRITICAL SCHEMA CORRECTIONS (Memorize these):
    11. **Table 'region'**: DOES NOT EXIST. `region` is a column in the `store` table. NEVER `JOIN region`.
    12. **Table 'loyalty_tier'**: Join via `customer`. 
        CORRECT: `JOIN loyalty_tier lt ON cust.loyalty_tier_id = lt.loyalty_tier_id`
        WRONG: `tier_id`, `segment_id`, or joining directly to sales.
    13. **Table 'promotion'**: Join via `purchase_order`.
        CORRECT: `JOIN purchase_order po ON s.order_id = po.order_id JOIN promotion p ON po.promo_id = p.promo_id`
        WRONG: Joining directly to sales.
    14. **Table 'return_order'**: Use this exact name. DO NOT use 'returns'.
    15. **Table 'shipment'**: Does NOT have `supplier_id`. Do NOT join shipment to supplier.
    16. **Table sales does not have name, it has store_id, to join with the store table use store_id**
    17. DO NOT select name from stores s alias; use name from store table instead
    COMPLEX REQUEST HANDLING (MySQL 5.7 Compatibility):
    17. **RFM Analysis**: Since `NTILE()` is not supported, calculate RAW values only:
        - Recency: `DATEDIFF(CURDATE(), MAX(s.sold_date))`
        - Frequency: `COUNT(DISTINCT s.order_id)`
        - Monetary: `SUM(s.sold_price)`
        Do NOT attempt to calculate 1-5 scores.
    18. **"Top Customers" / Ranking**: 
       - **STOP!** Do NOT try to find the top N *per group*. This is impossible in your MySQL version.
       - **INSTEAD**: Return the top N rows *overall*, ordered by the grouping column.
       - **User Request**: "Top 3 customers per store"
       - **Your Query**: `SELECT store_id, customer_id, SUM(sold_price) FROM sales GROUP BY store_id, customer_id ORDER BY store_id, SUM(sold_price) DESC LIMIT 100`
       - **NEVER** use `RANK()`, `ROW_NUMBER()`, or variables like `@rn`.
    19. **SLA Calculations**:
        - **Supplier SLA**: Use `restock_order`. (e.g. `restock_order.status = 'Received'`)
        - **Shipment/Delivery SLA**: Use `shipment`. (e.g. `DATEDIFF(sh.delivery_date, sh.expected_date)`)
    20. ALWAYS reference the correct table and alias when selecting columns.
    21. NEVER generate, guess, or include column names that do not exist in the actual schema.
    22. If a column name is not found in the schema, do not include it in the query.
    23. Use table aliases exactly as defined in the query logic.
    24. If a column required for the answer exists in a joined dimension table (e.g., store name exists in `store` table, not in `sales`), you must SELECT it from the correct joined table alias (`st.name`, not `s.name`).
    25. Output only MySQL SQL — no explanation, no assumptions, no invalid syntax.
    """
    else:  # PostgreSQL
        system_prompt = f"""You are AskSQL, a PostgreSQL expert.
    
    Database Schema:
    {schema_desc}
    
    Rules:
    1. Build ONE valid PostgreSQL SELECT query.
    2. Use ONLY tables and columns from the schema above.
    3. Do NOT query system tables.
    4. Always include LIMIT 100. No semicolons.
    
    CRITICAL SQL CONSTRAINTS:
    5. **STRICT ALIASING**: Always use short, unique table aliases (e.g., `s` for sales, `st` for store, `cust` for customer, `cat` for category). NEVER use the same alias for different tables.
    6. **NO DUPLICATE COLUMNS**: When joining, if a column exists in multiple tables, select it from ONE table only or alias it.

    CRITICAL SCHEMA CORRECTIONS (Memorize these):
    7. **Table 'region'**: DOES NOT EXIST. `region` is a column in the `store` table. NEVER `JOIN region`.
    8. **Table 'loyalty_tier'**: Join via `customer`. 
        CORRECT: `JOIN loyalty_tier lt ON cust.loyalty_tier_id = lt.loyalty_tier_id`
        WRONG: `tier_id`, `segment_id`, or joining directly to sales.
    9. **Table 'promotion'**: Join via `purchase_order`.
        CORRECT: `JOIN purchase_order po ON s.order_id = po.order_id JOIN promotion p ON po.promo_id = p.promo_id`
        WRONG: Joining directly to sales.
    10. **Table 'return_order'**: Use this exact name. DO NOT use 'returns'.
    """
    try:
        r = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role":"system","content":system_prompt},{"role":"user","content":nl_text}], temperature=0)
        response_text = r.choices[0].message.content.strip()
        
        # Extract SQL from code blocks if present
        # Look for ```sql ... ``` first
        sql_match = re.search(r"```sql\s*(.*?)\s*```", response_text, re.DOTALL | re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Look for generic ``` ... ```
            code_match = re.search(r"```\s*(.*?)\s*```", response_text, re.DOTALL)
            if code_match:
                sql = code_match.group(1).strip()
            else:
                # Fallback: assume the whole text is SQL
                sql = response_text.strip()
        
        # Clean up SQL
        sql = sql.replace(";", "").strip()
        
        # Ensure it starts with SELECT (simple heuristic to clean up any remaining prefix if regex failed or wasn't used)
        # This helps if the model returns "Here is the query: SELECT..." without code blocks
        if not sql.upper().startswith("SELECT") and "SELECT " in sql.upper():
             match = re.search(r"(SELECT\s+.*)", sql, re.DOTALL | re.IGNORECASE)
             if match:
                 sql = match.group(1)

        if not re.search(r"\blimit\b", sql.lower()):
            sql += " LIMIT 100"
        return sql
    except Exception as e:
        return f"SELECT 'SQL generation error: {e}' AS error_message LIMIT 100"

# ⚙ SQL query execution
def run_query(sql: str) -> pd.DataFrame:
    try:
        if DB_TYPE == "PostgreSQL":
            conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
        elif DB_TYPE == "MySQL":
            conn = mysql.connector.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
            
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


# 🎨 Premium UI Design System
from ui_utils import load_css_with_theme

# Inject CSS with theme variables
theme_vars = {
    'ROOT_BG': ROOT_BG,
    'ROOT_BG_SOLID': ROOT_BG_SOLID,
    'ROOT_TEXT': ROOT_TEXT,
    'CARD_BG': CARD_BG,
    'INPUT_BG': INPUT_BG,
    'CARD_BORDER': CARD_BORDER,
    'ACCENT': ACCENT,
    'ACCENT_HOVER': ACCENT_HOVER,
    'SECONDARY': SECONDARY,
    'SUCCESS': SUCCESS,
    'SHADOW': SHADOW,
    'GLOW': GLOW,
    'GRADIENT_PRIMARY': GRADIENT_PRIMARY,
    'GRADIENT_ACCENT': GRADIENT_ACCENT,
    'EXPANDER_ARROW': EXPANDER_ARROW
}

st.markdown(load_css_with_theme(theme_vars), unsafe_allow_html=True)



with st.container():
    st.markdown(f"""
    <div style="
        text-align: center; 
        margin-bottom: 20px;
        padding: 8px 24px;
        animation: fadeInUp 0.8s ease-out;
    ">
        <h1 style="
            font-size: 3.5rem;
            font-weight: 900;
            margin-bottom: 15px;
            background: {GRADIENT_PRIMARY};
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
            letter-spacing: -0.04em;
            line-height: 1;
            text-shadow: 0 4px 30px {ACCENT}40;
            filter: drop-shadow(0 0 20px {ACCENT}30);
        ">
            ✨ Ask Questions. Get Answers. ✨
        </h1>
        <div style="
            font-size: 1.25rem;
            font-weight: 500;
            color: {SECONDARY};
            max-width: 650px;
            margin: 0 auto;
            line-height: 1.7;
            letter-spacing: 0.02em;
        ">
            Transform natural language into powerful SQL queries instantly with our AI Agent
        </div>
    </div>
    """, unsafe_allow_html=True)

# Two-column layout
col_left, col_right = st.columns([1, 2], gap="large")

# LEFT COLUMN: Schema Browser
with col_left:
    with st.container(border=True):
        st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <div style="
                font-size: 1.15rem; 
                font-weight: 700; 
                color: {ACCENT}; 
                display: flex; 
                align-items: center; 
                gap: 10px;
                margin-bottom: 8px;
            ">
                🗄️ Database Schema
            </div>
            <div style="
                font-size: 0.9rem; 
                color: {SECONDARY}; 
                line-height: 1.5;
                font-weight: 400;
            ">
                Browse tables and columns
            </div>
        </div>
        """, unsafe_allow_html=True)
        if not TABLES:
            st.warning("⚠ No tables found in database.")
        else:
            selected_table = st.selectbox("Select Table", TABLES, label_visibility="collapsed")
            
            if selected_table:
                st.markdown(f"""
                <div style="
                    font-size: 0.95rem;
                    font-weight: 600;
                    color: {ROOT_TEXT};
                    margin: 20px 0 12px 0;
                ">
                    Columns in <code style="
                        background: {ACCENT}15;
                        color: {ACCENT};
                        padding: 3px 8px;
                        border-radius: 6px;
                        font-size: 0.9em;
                    ">{selected_table}</code>
                </div>
                """, unsafe_allow_html=True)
                cols = schema_objects.get(selected_table, [])
                
                # Render columns as chips
                chip_html = ""
                for c in cols:
                    chip_html += f'<span class="col-chip">{c}</span>'
                st.markdown(chip_html, unsafe_allow_html=True)
                
                st.markdown("---")

# RIGHT COLUMN: Query Console
with col_right:
    with st.container(border=True):
        st.markdown(f"""
        <div style="
            font-size: 1.15rem; 
            font-weight: 700; 
            color: {ROOT_TEXT}; 
            margin-bottom: 20px;
        ">
        ⚡ Ask Your Question
        </div>
        """, unsafe_allow_html=True)
        
        question = st.text_area(
            "Type your question in plain English:", 
            height=80, 
            placeholder="e.g., Show me the top 10 products by sales...",
            label_visibility="collapsed"
        )
        
        if st.button("🚀 Generate & Run SQL", type="primary", use_container_width=True):
            if not question.strip():
                st.warning("⚠️ Please enter a question first.")
            else:
                with st.spinner("🔮 Generating SQL..."):
                    sql = generate_sql(question)
                
                st.markdown(f"""
                <div style="
                    font-size: 1.05rem;
                    font-weight: 600;
                    color: {ROOT_TEXT};
                    margin: 24px 0 12px 0;
                ">
                    📝 Generated SQL
                </div>
                """, unsafe_allow_html=True)
                st.code(sql, language="sql")
                
                with st.spinner("⚡ Executing query..."):
                    df = run_query(sql)
                
                if df.empty:
                    st.info("ℹ️ Query returned no results.")
                else:
                    st.markdown(f"""
                    <div style="
                        font-size: 1.05rem;
                        font-weight: 600;
                        color: {ROOT_TEXT};
                        margin: 24px 0 12px 0;
                    ">
                        📊 Results <span style="
                            color: {SECONDARY};
                            font-weight: 500;
                            font-size: 0.9rem;
                        ">({len(df)} rows)</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True)
                    
                    # Download CSV
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download CSV",
                        csv,
                        "query_results.csv",
                        "text/csv",
                        key='download-csv'
                    )


# Footer
st.markdown(f"""
<div style="
    text-align: center; 
    margin-top: 64px;
    padding: 32px 0;
    border-top: 1px solid {CARD_BORDER};
">
    <div style="
        color: {SECONDARY}; 
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 8px;
    ">
        AI Data Studio
    </div>
    <div style="
        color: {SECONDARY}; 
        font-size: 0.85rem;
        opacity: 0.8;
    ">
        ai.data.studio.by@gmail.com
    </div>
</div>
""", unsafe_allow_html=True)


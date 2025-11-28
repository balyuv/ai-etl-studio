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
    st.header("🔌 Database Connection")
    
    # Connection Mode Selector
    connection_mode = st.radio(
        "Connection Mode",
        ["🔐 My Database", "🧪 Test Database"],
        help="Choose to connect to your own database or use the test database"
    )
    
    if connection_mode == "🧪 Test Database":
        # Try to load test database credentials
        test_db_config = load_test_db_credentials()
        
        if test_db_config:
            # Test database is configured
            st.session_state['db_config'] = test_db_config
            st.success("✅ Connected to Test Database")
            st.info(f"**Type:** {test_db_config['type']}\n\n**Host:** {test_db_config['host']}")
            
            # Admin option to reconfigure test database
            with st.expander("🔧 Admin: Reconfigure Test Database"):
                st.caption("⚠️ This will update the test database credentials for all users")
                with st.form("test_db_setup"):
                    test_db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"])
                    test_db_host = st.text_input("Host", value=test_db_config.get("host", ""))
                    test_db_port = st.text_input("Port", value=str(test_db_config.get("port", "")))
                    test_db_user = st.text_input("User", value=test_db_config.get("user", ""))
                    test_db_pass = st.text_input("Password", type="password")
                    test_db_name = st.text_input("Database Name", value=test_db_config.get("database", ""))
                    
                    if test_db_type == "PostgreSQL":
                        test_db_schema = st.text_input("Schema", value=test_db_config.get("schema", "public"))
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
                            st.rerun()
        else:
            # Test database not configured - show setup form
            st.warning("⚠️ Test database not configured")
            st.caption("Admin: Set up the test database credentials below")
            
            with st.form("test_db_setup"):
                st.caption("Configure Test Database (Encrypted Storage)")
                test_db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"])
                test_db_host = st.text_input("Host", value="localhost")
                test_db_port = st.text_input("Port", value="5432" if test_db_type == "PostgreSQL" else "3306")
                test_db_user = st.text_input("User", value="postgres" if test_db_type == "PostgreSQL" else "root")
                test_db_pass = st.text_input("Password", type="password")
                test_db_name = st.text_input("Database Name")
                
                if test_db_type == "PostgreSQL":
                    test_db_schema = st.text_input("Schema", value="public")
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
                        st.rerun()
    
    else:  # My Database mode
        # Load saved credentials from file if not in session
        if 'db_config' not in st.session_state:
            loaded_config = load_credentials()
            if loaded_config:
                st.session_state['db_config'] = loaded_config
                st.session_state['remember_me'] = True
        
        # Get saved values from session state if they exist
        saved_config = st.session_state.get('db_config', {})
        
        with st.form("db_creds"):
            st.caption("Enter Database Credentials")
            db_type = st.selectbox(
                "Database Type", 
                ["PostgreSQL", "MySQL"],
                index=0 if saved_config.get("type") == "PostgreSQL" else (1 if saved_config.get("type") == "MySQL" else 0)
            )
            db_host = st.text_input(
                "Host", 
                value=saved_config.get("host", "localhost"),
                help="Database host address",
                key="host_input"
            )
            db_port = st.text_input(
                "Port", 
                value=str(saved_config.get("port", "5432" if db_type == "PostgreSQL" else "3306")),
                help="Database port number",
                key="port_input"
            )
            db_user = st.text_input(
                "User", 
                value=saved_config.get("user", "postgres" if db_type == "PostgreSQL" else "root"),
                help="Database username",
                key="user_input"
            )
            db_pass = st.text_input(
                "Password", 
                type="password",
                value=saved_config.get("password", ""),
                help="Database password",
                key="pass_input"
            )
            db_name = st.text_input(
                "Database Name", 
                value=saved_config.get("database", "postgres" if db_type == "PostgreSQL" else ""),
                help="Name of the database to connect to",
                key="db_input"
            )
            
            # Schema is only relevant for PostgreSQL
            if db_type == "PostgreSQL":
                db_schema = st.text_input(
                    "Schema", 
                    value=saved_config.get("schema", "public"),
                    help="PostgreSQL schema name",
                    key="schema_input"
                )
            else:
                db_schema = None
            
            # Remember Me checkbox
            remember_me = st.checkbox(
                "💾 Remember credentials on this computer",
                value=st.session_state.get('remember_me', False),
                help="Saves credentials to ~/.asksql_credentials.json (base64 encoded)"
            )
                
            col1, col2 = st.columns(2)
            with col1:
                connect_btn = st.form_submit_button("🔌 Connect", use_container_width=True)
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
    
    # Show connection status (outside both modes)
    if 'db_config' in st.session_state:
        cfg = st.session_state['db_config']
        st.success(f"✅ Connected to **{cfg['type']}** at `{cfg['host']}:{cfg['port']}`")
        
        # Show if credentials are saved
        if CREDS_FILE.exists():
            st.caption("💾 Credentials saved to disk")



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
    3. Do NOT use schema/database prefixes (e.g., use 'table_name', NOT 'database.table_name').
    4. Do NOT query information_schema, mysql, or any system tables.
    5. If the user asks to "show tables" or "list tables", respond with: SELECT 'Available tables: {", ".join(TABLES)}' AS tables LIMIT 100
    6. If the user asks for "summary", infer the correct table from the schema.
    7. Always include LIMIT 100 if not specified.
    8. No semicolons.
    9. CRITICAL: When using JOINs, ALWAYS prefix column names with their table name/alias in the SELECT clause (e.g., 'product.product_id', 'sales.product_id') to avoid ambiguous column errors.
    10. CRITICAL: Make sure the columns exist in the tables before using them in the query.
    """
    else:  # PostgreSQL
        system_prompt = f"""You are AskSQL, a PostgreSQL expert.
    
    Database Schema:
    {schema_desc}
    
    Rules:
    1. Build ONE valid PostgreSQL SELECT query.
    2. Use ONLY tables and columns from the schema above.
    3. Do NOT query information_schema, pg_catalog, or any system tables.
    4. If the user asks to "show tables" or "list tables", respond with: SELECT 'Available tables: {", ".join(TABLES)}' AS tables LIMIT 100
    5. If the user asks for "summary", infer the correct table from the schema.
    6. Always include LIMIT 100 if not specified.
    7. No semicolons.
    8. CRITICAL: When using JOINs, ALWAYS prefix column names with their table name/alias in the SELECT clause (e.g., 'product.product_id', 'sales.product_id') to avoid ambiguous column errors.
    """
    try:
        r = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role":"system","content":system_prompt},{"role":"user","content":nl_text}], temperature=0)
        sql = r.choices[0].message.content.strip()
        sql = sql.replace(";", "").strip()
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
        return df
    except Exception as e:
        st.error(f"❌ SQL Execution Failed: {e}")
        return pd.DataFrame()

# 🎨 Premium UI Design System
# Header Layout with Theme Toggle
col_title, col_toggle = st.columns([7, 1])

with col_toggle:
    st.write("")
    st.write("")
    dark_mode = st.toggle("🌗", value=True)

if dark_mode:
    # Modern dark theme - inspired by VS Code, GitHub Dark
    ROOT_BG = "linear-gradient(135deg, #0d1117 0%, #161b22 100%)"
    ROOT_BG_SOLID = "#0d1117"
    ROOT_TEXT = "#e6edf3"
    CARD_BG = "rgba(22, 27, 34, 0.8)"
    CARD_BORDER = "rgba(48, 54, 61, 0.5)"
    ACCENT = "#58a6ff"
    ACCENT_HOVER = "#79c0ff"
    SECONDARY = "#8b949e"
    SUCCESS = "#3fb950"
    SHADOW = "0 8px 32px rgba(0, 0, 0, 0.4)"
    GLOW = "0 0 20px rgba(88, 166, 255, 0.3)"
else:
    # Modern light theme - inspired by Google Material, Apple Design
    ROOT_BG = "linear-gradient(135deg, #f6f8fa 0%, #ffffff 100%)"
    ROOT_BG_SOLID = "#ffffff"
    ROOT_TEXT = "#1f2328"
    CARD_BG = "rgba(255, 255, 255, 0.9)"
    CARD_BORDER = "rgba(208, 215, 222, 0.5)"
    ACCENT = "#0969da"
    ACCENT_HOVER = "#0550ae"
    SECONDARY = "#656d76"
    SUCCESS = "#1a7f37"
    SHADOW = "0 8px 32px rgba(31, 35, 40, 0.12)"
    GLOW = "0 0 20px rgba(9, 105, 218, 0.2)"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Root Styling */
    .stApp {{
        background: {ROOT_BG};
        color: {ROOT_TEXT};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    
    /* Smooth scrolling */
    html {{
        scroll-behavior: smooth;
    }}
    
    /* Typography Hierarchy */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: {ROOT_TEXT};
        line-height: 1.2;
    }}
    
    /* Premium Container Styling */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {{
        background: {CARD_BG};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid {CARD_BORDER};
        border-radius: 16px;
        padding: 24px;
        box-shadow: {SHADOW};
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    /* Glassmorphism Cards */
    .stContainer {{
        background: {CARD_BG};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid {CARD_BORDER};
        border-radius: 16px;
        box-shadow: {SHADOW};
    }}
    
    /* Column Chips - Modern Badge Design */
    .col-chip {{
        display: inline-flex;
        align-items: center;
        background: linear-gradient(135deg, {ACCENT}15, {ACCENT}25);
        color: {ACCENT};
        border: 1px solid {ACCENT}30;
        padding: 6px 14px;
        border-radius: 24px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 4px 6px 4px 0;
        transition: all 0.2s ease;
        letter-spacing: 0.01em;
    }}
    
    .col-chip:hover {{
        background: linear-gradient(135deg, {ACCENT}25, {ACCENT}35);
        border-color: {ACCENT}50;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px {ACCENT}20;
    }}
    
    /* Premium Button Styling */
    .stButton button {{
        background: linear-gradient(135deg, {ACCENT}, {ACCENT_HOVER});
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 28px;
        font-weight: 600;
        font-size: 0.95rem;
        letter-spacing: 0.02em;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 16px {ACCENT}30;
    }}
    
    .stButton button:hover {{
        transform: translateY(-2px);
        box-shadow: {GLOW}, 0 8px 24px {ACCENT}40;
    }}
    
    .stButton button:active {{
        transform: translateY(0);
    }}
    
    /* Form Inputs - Modern Design */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {{
        background: {CARD_BG};
        border: 1.5px solid {CARD_BORDER};
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 0.95rem;
        color: {ROOT_TEXT};
        transition: all 0.2s ease;
    }}
    
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {{
        border-color: {ACCENT};
        box-shadow: 0 0 0 3px {ACCENT}15;
        outline: none;
    }}
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background: {CARD_BG};
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-right: 1px solid {CARD_BORDER};
    }}
    
    [data-testid="stSidebar"] .stRadio label {{
        background: {CARD_BG};
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid {CARD_BORDER};
        margin: 4px 0;
        transition: all 0.2s ease;
    }}
    
    [data-testid="stSidebar"] .stRadio label:hover {{
        border-color: {ACCENT};
        background: {ACCENT}10;
    }}
    
    /* Code Block Styling */
    .stCodeBlock {{
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 12px;
        box-shadow: {SHADOW};
    }}
    
    code {{
        background: {ACCENT}15;
        color: {ACCENT};
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.9em;
        font-family: 'Monaco', 'Menlo', monospace;
    }}
    
    /* Dataframe Styling */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: {SHADOW};
    }}
    
    /* Success/Info/Warning Messages */
    .stSuccess, .stInfo, .stWarning {{
        border-radius: 12px;
        border-left: 4px solid {SUCCESS};
        padding: 16px 20px;
        backdrop-filter: blur(10px);
    }}
    
    /* Expander Styling */
    .streamlit-expanderHeader {{
        background: {CARD_BG};
        border-radius: 10px;
        border: 1px solid {CARD_BORDER};
        padding: 12px 16px;
        font-weight: 600;
        transition: all 0.2s ease;
    }}
    
    .streamlit-expanderHeader:hover {{
        border-color: {ACCENT};
        background: {ACCENT}10;
    }}
    
    /* Divider */
    hr {{
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, {CARD_BORDER}, transparent);
        margin: 32px 0;
    }}
    
    /* Scrollbar Styling */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {ROOT_BG_SOLID};
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {ACCENT}40;
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {ACCENT}60;
    }}
    
    /* Animations */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .stMarkdown, .stButton, .stTextInput {{
        animation: fadeIn 0.4s ease-out;
    }}
    
    /* Toggle Switch Styling */
    .stCheckbox {{
        padding: 8px;
    }}
</style>

<script>
    // Enable browser password manager
    document.addEventListener('DOMContentLoaded', function() {{
        const inputs = document.querySelectorAll('input[type="password"]');
        inputs.forEach(input => {{
            input.setAttribute('autocomplete', 'current-password');
        }});
        
        const userInputs = document.querySelectorAll('input[aria-label*="User"]');
        userInputs.forEach(input => {{
            input.setAttribute('autocomplete', 'username');
        }});
    }});
</script>
""", unsafe_allow_html=True)


with col_title:
    st.markdown(f"""
    <div style="
        text-align: center; 
        margin-bottom: 48px;
        padding: 32px 24px;
        animation: fadeIn 0.6s ease-out;
    ">
        <h1 style="
            font-size: 2.75rem;
            font-weight: 800;
            margin-bottom: 16px;
            background: linear-gradient(135deg, {ACCENT}, {ACCENT_HOVER});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
            letter-spacing: -0.03em;
            line-height: 1.1;
        ">
            Ask Questions. Get Answers.
        </h1>
        <div style="
            font-size: 1.1rem;
            font-weight: 400;
            color: {SECONDARY};
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.6;
            letter-spacing: 0.01em;
        ">
            AI-powered natural language to SQL assistant
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
                �️ Database Schema
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
            💬 Ask Your Question
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


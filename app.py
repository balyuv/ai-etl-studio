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
CREDS_FILE = Path.home() / ".asksql_credentials.json"

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
    
    # Show connection status
    if 'db_config' in st.session_state:
        cfg = st.session_state['db_config']
        st.success(f"✅ Connected to **{cfg['type']}** at `{cfg['host']}:{cfg['port']}`")
        
        # Show if credentials are saved
        if CREDS_FILE.exists():
            st.caption("💾 Credentials saved to disk")


if 'db_config' not in st.session_state:
    st.info("👈 Please enter your database credentials in the sidebar to get started.")
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

# 🎨 Themes & Styling
# 🎨 Themes & Styling
# Header Layout with Theme Toggle
col_title, col_toggle = st.columns([7, 1])

with col_toggle:
    st.write("")
    st.write("")
    dark_mode = st.toggle("🌗", value=True)

if dark_mode:
    ROOT_BG = "#0F172A"
    ROOT_TEXT = "#F8FAFC"
    CARD_BG = "#1E293B"
    ACCENT = "#38BDF8"
else:
    ROOT_BG = "#FFFFFF"
    ROOT_TEXT = "#0F172A"
    CARD_BG = "#F1F5F9"
    ACCENT = "#0284C7"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp {{
        background-color: {ROOT_BG};
        color: {ROOT_TEXT};
        font-family: 'Inter', sans-serif;
    }}
    
    /* Headings */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: {ROOT_TEXT};
    }}
    
    /* Chips for columns */
    .col-chip {{
        display: inline-block;
        background-color: {ACCENT}20;
        color: {ACCENT};
        border: 1px solid {ACCENT}40;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 2px 4px 2px 0;
    }}
    
    /* Button Styling */
    .stButton button {{
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }}
</style>

<script>
    // Enable browser password manager
    document.addEventListener('DOMContentLoaded', function() {{
        // Find password input and add autocomplete
        const inputs = document.querySelectorAll('input[type="password"]');
        inputs.forEach(input => {{
            input.setAttribute('autocomplete', 'current-password');
        }});
        
        // Find username/user inputs
        const userInputs = document.querySelectorAll('input[aria-label*="User"]');
        userInputs.forEach(input => {{
            input.setAttribute('autocomplete', 'username');
        }});
    }});
</script>
""", unsafe_allow_html=True)

with col_title:
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #6366f1, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
            filter: drop-shadow(0 2px 10px rgba(99, 102, 241, 0.2));
        ">
            ⚡ Talk to SQL Console ⚡
        </h1>
        <div style="
            font-size: 1.6rem;
            font-weight: 400;
            color: {ROOT_TEXT};
            opacity: 1.0;
            max-width: 700px;
            margin: 0 auto;
            line-height: 1.6;
        ">
            Ask in words. Run in SQL.
        </div>
    </div>
    """, unsafe_allow_html=True)

# Two-column layout
col_left, col_right = st.columns([1, 2], gap="large")

# LEFT COLUMN: Schema Browser
with col_left:
    with st.container(border=True):
        st.markdown(f"""
        <div style="margin-bottom: 15px;">
            <div style="font-size: 1.2rem; font-weight: 700; color: {ACCENT}; display: flex; align-items: center; gap: 8px;">
                🔎 Database Schema
            </div>
            <div style="font-size: 0.85rem; color: {ROOT_TEXT}; opacity: 0.65; margin-top: 4px; font-weight: 400;">
                Select a table to view its schema, then ask your question.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if not TABLES:
            st.warning("⚠ No tables found in database.")
        else:
            selected_table = st.selectbox("Select Table", TABLES, label_visibility="collapsed")
            
            if selected_table:
                st.markdown(f"**Columns in `{selected_table}`**")
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
        st.subheader("🧠 SQL Generator")
        
        question = st.text_area(
            "Ask a question about your data:", 
            height=100, 
            placeholder="e.g., Show me the top 10 users by total spend..."
        )
        
        if st.button("🚀 Generate & Run SQL", type="primary", use_container_width=True):
            if not question.strip():
                st.warning("Please enter a question first.")
            else:
                with st.spinner("Generating SQL..."):
                    sql = generate_sql(question)
                
                st.markdown("### Generated SQL")
                st.code(sql, language="sql")
                
                with st.spinner("Executing query..."):
                    df = run_query(sql)
                
                if df.empty:
                    st.info("Query returned no results.")
                else:
                    st.markdown(f"### Results ({len(df)} rows)")
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
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: {ROOT_TEXT}; opacity: 0.5; font-size: 0.9rem;'>"
    "Built with ❤️ by Balaji Yuvarajan :-) "
    "</div>", 
    unsafe_allow_html=True
)

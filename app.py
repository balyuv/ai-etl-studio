import os
import re
import pandas as pd
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Import refactored modules
from db_utils import (
    load_credentials, save_credentials, clear_saved_credentials,
    load_test_db_credentials, save_test_db_credentials,
    get_schema, run_query, credentials_exist
)
from ui_utils import load_css_with_theme
from ui_components import (
    render_sidebar_header, render_connection_status,
    render_main_header, render_schema_browser
)
from prompts import get_system_prompt

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

# 🎨 Premium UI Design System
with st.sidebar:
    st.write("")
    dark_mode = st.toggle("🌗 Dark Mode", value=True)

if dark_mode:
    # Vibrant dark theme with dramatic effects
    ROOT_BG = "linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%)"
    ROOT_BG_SOLID = "#0a0e27"
    ROOT_TEXT = "#ffffff"
    CARD_BG = "rgba(40, 48, 75, 0.75)"
    INPUT_BG = "rgba(255, 255, 255, 0.9)"
    INPUT_TEXT_COLOR = "#000000"
    CARD_BORDER = "rgba(88, 166, 255, 0.3)"
    ACCENT = "#00d4ff"
    ACCENT_HOVER = "#00f0ff"
    SECONDARY = "#ffffff"
    SUCCESS = "#00ff88"
    SHADOW = "0 20px 60px rgba(0, 0, 0, 0.6)"
    GLOW = "0 0 40px rgba(0, 212, 255, 0.5)"
    GRADIENT_PRIMARY = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    GRADIENT_ACCENT = "linear-gradient(135deg, #00d4ff 0%, #0099ff 100%)"
    EXPANDER_ARROW = "#00d4ff"
else:
    # Vibrant light theme with dramatic effects
    ROOT_BG = "linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 50%, #f8f9ff 100%)"
    ROOT_BG_SOLID = "#ffffff"
    ROOT_TEXT = "#1a202c"
    CARD_BG = "rgba(255, 255, 255, 0.85)"
    INPUT_BG = "rgba(255, 255, 255, 0.9)"
    INPUT_TEXT_COLOR = "#000000"
    CARD_BORDER = "rgba(102, 126, 234, 0.25)"
    ACCENT = "#667eea"
    ACCENT_HOVER = "#5568d3"
    SECONDARY = "#718096"
    SUCCESS = "#48bb78"
    SHADOW = "0 20px 60px rgba(102, 126, 234, 0.25)"
    GLOW = "0 0 40px rgba(102, 126, 234, 0.4)"
    GRADIENT_PRIMARY = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    GRADIENT_ACCENT = "linear-gradient(135deg, #667eea 0%, #0099ff 100%)"
    EXPANDER_ARROW = "#FFB800"

# Inject CSS with theme variables
theme_vars = {
    'ROOT_BG': ROOT_BG,
    'ROOT_BG_SOLID': ROOT_BG_SOLID,
    'ROOT_TEXT': ROOT_TEXT,
    'CARD_BG': CARD_BG,
    'INPUT_BG': INPUT_BG,
    'INPUT_TEXT_COLOR': INPUT_TEXT_COLOR,
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

# 🔌 Sidebar Database Connection
with st.sidebar:
    render_sidebar_header(CARD_BORDER, ACCENT, SECONDARY)
    
    st.markdown(f"""
    <div style="font-size: 0.9rem; font-weight: 600; margin-bottom: 12px; color: {SECONDARY};">
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
        test_db_config = load_test_db_credentials()
        if test_db_config:
            st.session_state['db_config'] = test_db_config
            st.success("✅ Connected to Test Database")
            st.info(f"**Type:** {test_db_config['type']}\n\n**Host:** {test_db_config['host']}")
            
            with st.expander("🔧 Admin: Reconfigure Test Database"):
                st.caption("⚠️ This will update the test database credentials for all users")
                with st.form("test_db_reconfig_form"):
                    test_db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="reconfig_type")
                    test_db_host = st.text_input("Host", value=test_db_config.get("host", ""), key="reconfig_host")
                    test_db_port = st.text_input("Port", value=str(test_db_config.get("port", "")), key="reconfig_port")
                    test_db_user = st.text_input("User", value=test_db_config.get("user", ""), key="reconfig_user")
                    test_db_pass = st.text_input("Password", type="password", key="reconfig_pass")
                    test_db_name = st.text_input("Database Name", value=test_db_config.get("database", ""), key="reconfig_name")
                    test_db_schema = st.text_input("Schema", value=test_db_config.get("schema", "public"), key="reconfig_schema") if test_db_type == "PostgreSQL" else None
                    
                    if st.form_submit_button("💾 Update Test Database", use_container_width=True):
                        new_config = {
                            "type": test_db_type, "host": test_db_host, "port": test_db_port,
                            "user": test_db_user, "password": test_db_pass, "database": test_db_name,
                            "schema": test_db_schema
                        }
                        if save_test_db_credentials(new_config):
                            st.session_state['db_config'] = new_config
                            st.success("✅ Test database updated!")
        else:
            st.warning("⚠️ Test database not configured")
            with st.form("test_db_initial_setup_form"):
                st.caption("Configure Test Database (Encrypted Storage)")
                test_db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL"], key="initial_type")
                test_db_host = st.text_input("Host", value="localhost", key="initial_host")
                test_db_port = st.text_input("Port", value="5432" if test_db_type == "PostgreSQL" else "3306", key="initial_port")
                test_db_user = st.text_input("User", value="postgres" if test_db_type == "PostgreSQL" else "root", key="initial_user")
                test_db_pass = st.text_input("Password", type="password", key="initial_pass")
                test_db_name = st.text_input("Database Name", key="initial_name")
                test_db_schema = st.text_input("Schema", value="public", key="initial_schema") if test_db_type == "PostgreSQL" else None
                
                if st.form_submit_button("💾 Save Test Database", use_container_width=True):
                    config = {
                        "type": test_db_type, "host": test_db_host, "port": test_db_port,
                        "user": test_db_user, "password": test_db_pass, "database": test_db_name,
                        "schema": test_db_schema
                    }
                    if save_test_db_credentials(config):
                        st.session_state['db_config'] = config
                        st.success("✅ Test database configured!")
    else:
        if 'db_config' not in st.session_state:
            loaded_config = load_credentials()
            if loaded_config:
                st.session_state['db_config'] = loaded_config
                st.session_state['remember_me'] = True
        
        saved_config = st.session_state.get('db_config', {})
        st.markdown(f"<div style='font-size: 0.9rem; font-weight: 600; margin: 24px 0 16px 0; color: {SECONDARY}; border-bottom: 1px solid {CARD_BORDER}; padding-bottom: 8px;'>📊 DATABASE SETTINGS</div>", unsafe_allow_html=True)
        
        with st.form("db_creds"):
            db_type = st.selectbox("🗄️ Database Type", ["PostgreSQL", "MySQL"], index=0 if saved_config.get("type") == "PostgreSQL" else (1 if saved_config.get("type") == "MySQL" else 0))
            st.markdown(f"<div style='margin: 16px 0 8px 0; font-size: 0.85rem; font-weight: 600; color: {SECONDARY};'>CONNECTION DETAILS</div>", unsafe_allow_html=True)
            col1, col2 = st.columns([2, 1])
            with col1: db_host = st.text_input("🌐 Server / Host", value=saved_config.get("host", "localhost"), placeholder="e.g., localhost", key="host_input")
            with col2: db_port = st.text_input("🔌 Port", value=str(saved_config.get("port", "5432" if db_type == "PostgreSQL" else "3306")), placeholder="5432", key="port_input")
            db_name = st.text_input("💾 Database Name", value=saved_config.get("database", "postgres" if db_type == "PostgreSQL" else ""), placeholder="Enter database name", key="db_input")
            db_schema = st.text_input("📁 Schema", value=saved_config.get("schema", "public"), placeholder="public", key="schema_input") if db_type == "PostgreSQL" else None
            
            st.markdown(f"<div style='margin: 16px 0 8px 0; font-size: 0.85rem; font-weight: 600; color: {SECONDARY};'>AUTHENTICATION</div>", unsafe_allow_html=True)
            db_user = st.text_input("👤 Username", value=saved_config.get("user", "postgres" if db_type == "PostgreSQL" else "root"), placeholder="Enter username", key="user_input")
            db_pass = st.text_input("🔑 Password", type="password", value=saved_config.get("password", ""), placeholder="Enter password", key="pass_input")
            
            st.markdown("<div style='margin: 16px 0 8px 0;'></div>", unsafe_allow_html=True)
            remember_me = st.checkbox("💾 Remember credentials on this computer", value=st.session_state.get('remember_me', False), help="Saves credentials to ~/.asksql_credentials.json (base64 encoded)")
            st.markdown("<div style='margin: 16px 0;'></div>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1: connect_btn = st.form_submit_button("✅ Connect", type="primary", use_container_width=True)
            with col2: clear_btn = st.form_submit_button("🗑️ Clear", use_container_width=True)
        
        if connect_btn:
            st.session_state['db_config'] = {"type": db_type, "host": db_host, "port": db_port, "user": db_user, "password": db_pass, "database": db_name, "schema": db_schema}
            st.session_state['remember_me'] = remember_me
            if remember_me:
                if save_credentials(st.session_state['db_config']): st.success("✅ Connected & credentials saved!")
                else: st.success("✅ Connected!")
            else:
                clear_saved_credentials()
                st.success("✅ Connected!")
            st.rerun()
        
        if clear_btn:
            if 'db_config' in st.session_state: del st.session_state['db_config']
            if 'remember_me' in st.session_state: del st.session_state['remember_me']
            clear_saved_credentials()
            st.info("🗑️ Credentials cleared!")
            st.rerun()

    if 'db_config' in st.session_state:
        render_connection_status(st.session_state['db_config'], CARD_BORDER, SECONDARY)
        if credentials_exist():
            st.markdown("""<div style="font-size: 0.8rem; color: #718096; text-align: center; padding: 8px; background: rgba(102, 126, 234, 0.1); border-radius: 8px;">💾 Credentials saved locally</div>""", unsafe_allow_html=True)

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

schema_objects = get_schema(DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, DB_SCHEMA)

if "_error" in schema_objects:
    schema_objects = {}
    TABLES = []
    STATUS = False
else:
    TABLES = list(schema_objects.keys())
    STATUS = True

def generate_sql(nl_text: str) -> str:
    if not STATUS:
        return "SELECT 'Schema unavailable' AS error_message LIMIT 100"

    schema_desc = "\n".join(f'TABLE "{t}" (columns: {", ".join(schema_objects[t])})' for t in TABLES)
    system_prompt = get_system_prompt(DB_TYPE, schema_desc)
    
    try:
        r = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role":"system","content":system_prompt},{"role":"user","content":nl_text}], temperature=0)
        response_text = r.choices[0].message.content.strip()
        
        sql_match = re.search(r"```sql\s*(.*?)\s*```", response_text, re.DOTALL | re.IGNORECASE)
        if sql_match: sql = sql_match.group(1).strip()
        else:
            code_match = re.search(r"```\s*(.*?)\s*```", response_text, re.DOTALL)
            if code_match: sql = code_match.group(1).strip()
            else: sql = response_text.strip()
        
        sql = sql.replace(";", "").strip()
        if not sql.upper().startswith("SELECT") and "SELECT " in sql.upper():
             match = re.search(r"(SELECT\s+.*)", sql, re.DOTALL | re.IGNORECASE)
             if match: sql = match.group(1)

        if not re.search(r"\blimit\b", sql.lower()): sql += " LIMIT 100"
        return sql
    except Exception as e:
        return f"SELECT 'SQL generation error: {e}' AS error_message LIMIT 100"

render_main_header(GRADIENT_PRIMARY, ACCENT, SECONDARY)

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    with st.container(border=True):
        selected_table = render_schema_browser(ACCENT, SECONDARY, ROOT_TEXT, TABLES, schema_objects)

with col_right:
    with st.container(border=True):
        st.markdown(f"""<div style="font-size: 1.15rem; font-weight: 700; color: {ROOT_TEXT}; margin-bottom: 20px;">⚡ Ask Your Question</div>""", unsafe_allow_html=True)
        question = st.text_area("Type your question in plain English:", height=80, placeholder="e.g., Show me the top 10 products by sales...", label_visibility="collapsed")
        
        if st.button("🚀 Generate & Run SQL", type="primary", use_container_width=True):
            if not question.strip():
                st.warning("⚠️ Please enter a question first.")
            else:
                with st.spinner("🔮 Generating SQL..."):
                    sql = generate_sql(question)
                
                st.markdown(f"""<div style="font-size: 1.05rem; font-weight: 600; color: {ROOT_TEXT}; margin: 24px 0 12px 0;">📝 Generated SQL</div>""", unsafe_allow_html=True)
                st.code(sql, language="sql")
                
                with st.spinner("⚡ Executing query..."):
                    df = run_query(DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, sql)
                
                if df.empty:
                    st.info("ℹ️ Query returned no results.")
                else:
                    st.markdown(f"""<div style="font-size: 1.05rem; font-weight: 600; color: {ROOT_TEXT}; margin: 24px 0 12px 0;">📊 Results <span style="color: {SECONDARY}; font-weight: 500; font-size: 0.9rem;">({len(df)} rows)</span></div>""", unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download CSV", csv, "query_results.csv", "text/csv", key='download-csv')

st.markdown(f"""
<div style="text-align: center; margin-top: 64px; padding: 32px 0; border-top: 1px solid {CARD_BORDER};">
    <div style="color: {SECONDARY}; font-size: 0.9rem; font-weight: 500; margin-bottom: 8px;">AI Data Studio</div>
    <div style="color: {SECONDARY}; font-size: 0.85rem; opacity: 0.8;">ai.data.studio.by@gmail.com</div>
</div>
""", unsafe_allow_html=True)

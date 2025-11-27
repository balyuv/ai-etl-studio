import os
import json
import re
import pandas as pd
import streamlit as st
import psycopg2
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

# 🗂 Load PostgreSQL credentials
CONFIG_FILE = "user_db_creds.json"
try:
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
except Exception:
    st.error("❌ Database credentials JSON missing or invalid")
    st.stop()

DB_HOST = cfg.get("host")
DB_PORT = int(cfg.get("port", 5432))
DB_USER = cfg.get("user")
DB_PASS = cfg.get("password")
DB_NAME = cfg.get("database")
DB_SCHEMA = cfg.get("schema", "public")

if not DB_HOST or not DB_USER or not DB_NAME:
    st.error("❌ Database creds incomplete")
    st.stop()

# 🔍 Safe Schema Discovery
@st.cache_resource(ttl=300, show_spinner=True)
def get_schema():
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = %s AND table_type='BASE TABLE'
            ORDER BY table_name
        """, (DB_SCHEMA,))
        tables = [r[0] for r in cur.fetchall()]
        schema = {}
        for t in tables:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s
                ORDER BY ordinal_position
            """, (DB_SCHEMA, t))
            schema[t] = [c[0] for c in cur.fetchall()]
        cur.close()
        conn.close()
        return schema
    except Exception as e:
        return {"_error": str(e)}

schema_objects = get_schema()

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
    system_prompt = f"""You are AskSQL, a PostgreSQL expert.
    
    Database Schema:
    {schema_desc}
    
    Rules:
    1. Build ONE valid PostgreSQL SELECT query.
    2. Use ONLY tables and columns from the schema above.
    3. If the user asks for "summary", infer the correct table from the schema.
    4. Always include LIMIT 100 if not specified.
    5. No semicolons.
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
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
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
            ⚡ AskSQL Console
        </h1>
        <div style="
            font-size: 1.1rem;
            font-weight: 500;
            color: {ROOT_TEXT};
            opacity: 0.8;
            max-width: 700px;
            margin: 0 auto;
            line-height: 1.6;
        ">
            Transform natural language into SQL queries instantly.
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

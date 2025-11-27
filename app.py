# app.py
"""Streamlit app for Natural‑Language to SQL conversion using OpenAI.
Professional UI overhaul to match modern dashboard aesthetics.
"""

import os
import json
import re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import openai
from difflib import get_close_matches

# ---------------------------------------------------------------------------
# Configuration & Setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI ETL Studio",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OpenAI API key not found. Please set OPENAI_API_KEY in a .env file.")
    st.stop()
openai.api_key = openai_api_key

# ---------------------------------------------------------------------------
# Custom CSS for Professional UI
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Dark theme background overrides */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1e293b;
        border-right: 1px solid #334155;
    }

    /* Input fields */
    .stTextInput input, .stTextArea textarea {
        background-color: #0f172a;
        border: 1px solid #334155;
        color: #f8fafc;
        border-radius: 0.5rem;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #38bdf8;
        box-shadow: 0 0 0 1px #38bdf8;
    }

    /* Primary Button */
    .stButton button {
        background-color: #38bdf8;
        color: #0f172a;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        transition: all 0.2s;
        width: 100%;
    }
    .stButton button:hover {
        background-color: #0ea5e9;
        color: #fff;
        border: none;
    }

    /* Card-like containers for results */
    .css-1r6slb0 {
        background-color: #1e293b;
        padding: 1.5rem;
        border-radius: 1rem;
        border: 1px solid #334155;
    }

    /* Headers */
    h1, h2, h3 {
        color: #f8fafc;
        font-weight: 700;
    }
    h1 { font-size: 2rem; }
    h2 { font-size: 1.5rem; color: #38bdf8; }
    
    /* Code block styling */
    .stCode {
        background-color: #000 !important;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Logic: SQL Generation & Execution
# ---------------------------------------------------------------------------

def fetch_all_tables(cfg: dict) -> list[str]:
    """Fetch all table names from the database."""
    try:
        conn = mysql.connector.connect(**cfg)
        cur = conn.cursor()
        cur.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
            (cfg["database"],),
        )
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return tables
    except Exception:
        return []

def get_table_columns(table_name: str, cfg: dict) -> list[str]:
    """Fetch column names for a specific table."""
    try:
        conn = mysql.connector.connect(**cfg)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (cfg["database"], table_name),
        )
        cols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return cols
    except Exception:
        return []

def guess_tables(nl: str, tables: list[str]) -> list[str]:
    """Identify table names from natural language query."""
    cleaned = re.sub(r"[.,;!?]", " ", nl.lower())
    words = cleaned.split()
    found = set()
    for i in range(len(words)):
        for length in range(1, 4):
            if i + length > len(words):
                break
            gram = "_".join(words[i : i + length])
            if gram in tables:
                found.add(gram)
            else:
                matches = get_close_matches(gram, tables, n=1, cutoff=0.7)
                if matches:
                    found.add(matches[0])
    return list(found)

def generate_sql(nl_query: str) -> str:
    """Generate SQL using OpenAI with schema awareness."""
    cfg = st.session_state.get("db_cfg", {})
    schema_hint = ""
    
    if cfg and all(cfg.values()):
        all_tables = fetch_all_tables(cfg)
        guessed_tables = guess_tables(nl_query, all_tables)
        
        if guessed_tables:
            hints = []
            for t in guessed_tables:
                cols = get_table_columns(t, cfg)
                if cols:
                    hints.append(f"Table `{t}` columns: {', '.join(cols)}")
            if hints:
                schema_hint = "Schema info: " + "; ".join(hints) + ". "

    system_prompt = (
        "You are an assistant that converts natural language questions into a single valid MySQL SELECT statement. "
        + schema_hint
        + "IMPORTANT: When joining tables, ensure all output columns have UNIQUE names. "
        + "Use aliases (e.g. t1.id AS t1_id) or select specific columns to avoid duplicates. "
        + "Return ONLY the SQL query without any explanation, markdown, or surrounding text."
    )

    client = openai.OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": nl_query},
        ],
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()
    return sql if sql.endswith(";") else sql + ";"

def run_query(sql: str, cfg: dict) -> pd.DataFrame:
    """Execute SQL query."""
    try:
        conn = mysql.connector.connect(**cfg)
        df = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Error as e:
        raise RuntimeError(f"MySQL error: {e}")

# ---------------------------------------------------------------------------
# UI Layout
# ---------------------------------------------------------------------------

# Sidebar: Database Configuration
with st.sidebar:
    st.title("AI ETL Studio")
    st.markdown("### Database Connection")
    
    CONFIG_FILE = "db_config.json"
    if "db_cfg" not in st.session_state:
        try:
            with open(CONFIG_FILE, "r") as f:
                st.session_state["db_cfg"] = json.load(f)
        except:
            st.session_state["db_cfg"] = {"host": "", "user": "", "password": "", "database": ""}
    
    db_cfg = st.session_state["db_cfg"]
    
    new_host = st.text_input("Host", value=db_cfg.get("host", ""))
    new_user = st.text_input("User", value=db_cfg.get("user", ""))
    new_pass = st.text_input("Password", type="password", value=db_cfg.get("password", ""))
    new_db = st.text_input("Database", value=db_cfg.get("database", ""))
    
    # Update session state
    db_cfg.update({"host": new_host, "user": new_user, "password": new_pass, "database": new_db})

    if st.button("Save Settings"):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(db_cfg, f, indent=2)
            st.success("Saved!")
        except Exception as e:
            st.error(f"Error: {e}")

# Main Content Area
st.title("Natural Language Query")
st.markdown("Ask questions about your data in plain English.")

# Search Bar Area
col1, col2 = st.columns([4, 1])
with col1:
    nl_query = st.text_area("Query", height=100, placeholder="e.g., Show total sales per month for 2023", label_visibility="collapsed")
with col2:
    st.markdown("<div style='height: 1.8rem'></div>", unsafe_allow_html=True) # Spacer
    run_btn = st.button("Run Query", use_container_width=True)

# Results Area
if run_btn:
    if not nl_query.strip():
        st.warning("Please enter a query.")
    elif not all(db_cfg.values()):
        st.warning("Please configure the database in the sidebar.")
    else:
        # 1. Generate SQL
        with st.spinner("Generating SQL..."):
            try:
                sql = generate_sql(nl_query)
                st.session_state['last_sql'] = sql
            except Exception as e:
                st.error(f"Generation Error: {e}")
                st.stop()

        # 2. Execute SQL
        with st.spinner("Executing..."):
            try:
                df = run_query(sql, db_cfg)
                st.session_state['last_df'] = df
            except Exception as e:
                st.error(f"Execution Error: {e}")

# Display Results (Persistent across reruns if in session state)
if 'last_sql' in st.session_state:
    st.markdown("### Generated SQL")
    st.code(st.session_state['last_sql'], language="sql")

if 'last_df' in st.session_state:
    df = st.session_state['last_df']
    if not df.empty:
        st.markdown(f"### Results ({len(df)} rows)")
        
        # Chart
        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) >= 2:
            # Convert Index to list to avoid "truth value of Index is ambiguous" error
            st.bar_chart(df, x=df.columns[0], y=numeric_cols[:2].tolist())
        
        # Table
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Query executed successfully but returned no results.")

# Footer
st.markdown("---")
st.caption("© 2025 AI ETL Studio | Powered by OpenAI & Streamlit")

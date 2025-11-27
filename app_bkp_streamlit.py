# app.py
"""Streamlit app for Natural‑Language to SQL conversion using OpenAI.

Features
--------
- Sidebar to configure MySQL connection (host, user, password, database).
- Text area for the user to type a natural‑language question.
- Calls OpenAI Chat Completion (gpt‑3.5‑turbo) to generate a single SELECT statement.
- Executes the generated SQL against the configured MySQL database.
- Displays the SQL, the result table and, when the result contains numeric columns, a bar chart.
- Uses a dark theme (Streamlit's built‑in theming) for a professional look.
"""

import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import openai

# ---------------------------------------------------------------------------
# Load environment variables (OpenAI API key)
# ---------------------------------------------------------------------------
load_dotenv()  # looks for a .env file in the current working directory
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OpenAI API key not found. Please set OPENAI_API_KEY in a .env file.")
    st.stop()
openai.api_key = openai_api_key

# ---------------------------------------------------------------------------
# Helper: generate SQL from natural language using OpenAI
# ---------------------------------------------------------------------------
def generate_sql(nl_query: str) -> str:
    """Convert natural language to a MySQL SELECT statement.
    This version tries to infer the target table even when the user writes
    phrases like "store ny" or "store in ny" and maps them to a table name
    such as ``store_ny``. It also fetches the column list for the guessed
    table and adds it to the system prompt so the model can pick the correct
    column (e.g., ``sales_amount`` instead of a generic ``sales``).
    """
    import re
    from difflib import get_close_matches

    # ------------------------------------------------------------------
    # Helper: fetch all table names from the DB (cached per session)
    # ------------------------------------------------------------------
    def fetch_all_tables(cfg: dict) -> list[str]:
        try:
            conn = mysql.connector.connect(
                host=cfg["host"],
                user=cfg["user"],
                password=cfg["password"],
                database=cfg["database"],
            )
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

    # ------------------------------------------------------------------
    # Helper: guess table names from the natural‑language query
    # ------------------------------------------------------------------
    def guess_tables(nl: str, tables: list[str]) -> list[str]:
        # Normalise the query: lower case, remove punctuation
        cleaned = re.sub(r"[.,;!?]", " ", nl.lower())
        words = cleaned.split()
        found = set()
        # Look for patterns like "store ny" -> "store_ny"
        for i in range(len(words)):
            for length in range(1, 4):  # n-grams of length 1 to 3
                if i + length > len(words):
                    break
                gram = "_".join(words[i : i + length])
                # Exact match
                if gram in tables:
                    found.add(gram)
                else:
                    # Fuzzy match
                    matches = get_close_matches(gram, tables, n=1, cutoff=0.7)
                    if matches:
                        found.add(matches[0])
        return list(found)

    # ------------------------------------------------------------------
    # Helper: fetch column names for a given table
    # ------------------------------------------------------------------
    def get_table_columns(table_name: str, cfg: dict) -> list[str]:
        try:
            conn = mysql.connector.connect(
                host=cfg["host"],
                user=cfg["user"],
                password=cfg["password"],
                database=cfg["database"],
            )
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

    # ------------------------------------------------------------------
    # Build the system prompt with schema hints if we can infer tables
    # ------------------------------------------------------------------
    cfg = st.session_state.get("db_cfg", {})
    schema_hint = ""
    if cfg:
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

    # ------------------------------------------------------------------
    # Call OpenAI with the enriched prompt
    # ------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Helper: execute SQL and return a pandas DataFrame
# ---------------------------------------------------------------------------
def run_query(sql: str, cfg: dict) -> pd.DataFrame:
    """Execute *sql* against the MySQL server described by *cfg*.
    Returns a DataFrame; raises an exception on failure.
    """
    try:
        conn = mysql.connector.connect(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
        )
        df = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Error as e:
        raise RuntimeError(f"MySQL error: {e}")

# ---------------------------------------------------------------------------
# UI – Sidebar: DB configuration
# ---------------------------------------------------------------------------
st.set_page_config(page_title="NL‑to‑SQL", layout="wide", initial_sidebar_state="expanded")
st.title("🧠 Natural Language → SQL (Streamlit)")

st.sidebar.header("Database connection")
# Path for persisting DB config
CONFIG_FILE = "db_config.json"

# Load persisted config if available and not already in session_state
if "db_cfg" not in st.session_state:
    # try to read from file
    try:
        with open(CONFIG_FILE, "r") as f:
            persisted = json.load(f)
    except Exception:
        persisted = {"host": "", "user": "", "password": "", "database": ""}
    st.session_state["db_cfg"] = persisted

# Reference the session_state dict
db_cfg = st.session_state["db_cfg"]
# UI inputs – values come from session_state (persisted or default)
db_cfg["host"] = st.sidebar.text_input("Host", value=db_cfg.get("host", ""))
db_cfg["user"] = st.sidebar.text_input("User", value=db_cfg.get("user", ""))
db_cfg["password"] = st.sidebar.text_input("Password", type="password", value=db_cfg.get("password", ""))
db_cfg["database"] = st.sidebar.text_input("Database", value=db_cfg.get("database", ""))

# Save button – writes current config to file for future sessions
if st.sidebar.button("Save Settings"):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(db_cfg, f, indent=2)
        st.sidebar.success("Database configuration saved.")
    except Exception as e:
        st.sidebar.error(f"Failed to save config: {e}")

# ---------------------------------------------------------------------------
# Main panel: NL input and conversion
# ---------------------------------------------------------------------------
nl_query = st.text_area("Enter your question in natural language", height=150)
if st.button("Convert & Run"):
    if not nl_query.strip():
        st.warning("Please type a question.")
    elif not all(db_cfg.values()):
        st.warning("Please fill in all database connection fields in the sidebar.")
    else:
        with st.spinner("Generating SQL…"):
            try:
                sql = generate_sql(nl_query)
                st.subheader("Generated SQL")
                st.code(sql, language="sql")
            except Exception as e:
                st.error(f"Failed to generate SQL: {e}")
                st.stop()
        with st.spinner("Running query…"):
            try:
                df = run_query(sql, db_cfg)
                if df.empty:
                    st.info("Query executed successfully – no rows returned.")
                else:
                    st.subheader("Results")
                    st.dataframe(df)
                    # If there are at least two numeric columns, show a simple bar chart
                    numeric_cols = df.select_dtypes(include="number").columns
                    if len(numeric_cols) >= 2:
                        st.subheader("Bar chart (first two numeric columns)")
                        chart_data = df[numeric_cols[:2]]
                        st.bar_chart(chart_data)
            except Exception as e:
                st.error(f"SQL execution error: {e}")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.caption("Powered by OpenAI and Streamlit. © 2025 BY AI ETL Studio.")

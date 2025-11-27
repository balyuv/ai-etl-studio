import os
import json
import pandas as pd
import streamlit as st
import textwrap  # ✅ required for dedent
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

# -----------------------------
# ✅ Hard-coded AWS RDS MySQL
# -----------------------------

with open("db_config.json", "r") as f:
    cfg = json.load(f)

DB_HOST = cfg["host"]
DB_USER = cfg["user"]
DB_PASS = cfg["password"]
DB_NAME = cfg["database"]

# -----------------------------
# ✅ OpenAI client
# -----------------------------
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OpenAI API key missing. Set it in .env")
    st.stop()

client = OpenAI(api_key=openai_api_key)

# -----------------------------
# Helper: Generate SQL from English → MySQL 5.5 compatible SELECT
# -----------------------------
def generate_sql(nl: str) -> str:
    """Generate one SELECT query grounded to your DB schema."""
    sys_prompt = """
You are an expert MySQL 5.5 query generator.

Rules:
- Output ONLY ONE SQL query.
- Must be SELECT only (read-only).
- No semicolon at end.
- Include LIMIT 100 unless user asks otherwise.
- Use only MySQL 5.5 compatible syntax.
"""
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system","content":sys_prompt},
            {"role":"user","content":nl},
        ],
        temperature=0,
    )
    sql = resp.choices[0].message.content.strip()

    if not sql.lower().startswith("select"):
        st.error("Generated query is not SELECT. Blocked.")
        st.stop()

    return sql

# -----------------------------
# Helper: Run generated SQL on AWS RDS MySQL
# -----------------------------
def run_query(sql: str):
    cfg = {"host":DB_HOST, "user":DB_USER, "password":DB_PASS, "database":DB_NAME}
    try:
        conn = mysql.connector.connect(**cfg)
        df = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Query execution failed: {e}")
        st.stop()


# -----------------------------
# 🎨 UI – Professional Layout
# -----------------------------
st.set_page_config(page_title="AI ETL Studio", layout="wide")

st.markdown("""
<div style="
    background:#11151c;
    padding:24px;
    border-radius:12px;
    border:1px solid rgba(0,255,255,0.2);
    margin-bottom:22px;
">
  <h1 style="margin:0;font-size:28px;">🧱 AI ETL Studio</h1>
  <p style="opacity:0.7;font-size:16px;margin:6px 0 0 0;">
    Natural Language SQL Runner (MySQL 5.5 on AWS RDS)
  </p>
</div>
""", unsafe_allow_html=True)


st.sidebar.header("🔒 Database (hardcoded)")

st.sidebar.code(textwrap.dedent(f"""
Host: {DB_HOST}
User: {DB_USER}
Database: {DB_NAME}
Password: {'•'*8} (hidden)
"""))


user_q = st.text_area(
    "Ask a question about your data in English:",
    height=140,
    placeholder="Example: Show top 10 NY stores by annual sales"
)

if st.button("🚀 Convert to SQL & Run"):
    if not user_q.strip():
        st.warning("Enter a question")
        st.stop()

    with st.spinner("Generating SQL…"):
        sql = generate_sql(user_q)
        st.subheader("Generated SQL")
        st.code(sql, "sql")

    with st.spinner("Running on AWS RDS…"):
        df = run_query(sql)

    if df.empty:
        st.info("No rows returned")
    else:
        st.subheader("Query Results")
        st.dataframe(df, use_container_width=True)

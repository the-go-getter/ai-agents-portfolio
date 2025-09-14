"""
DataScribe Agent
================
Translates a natural-language analytics question into SQL (for SQLite demo),
executes it, and returns rows. This demonstrates NL->SQL planning and simple data access.

Endpoint:
- POST /query  -> { question } -> { sql, rows }
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import pandas as pd
from common.llm_utils import complete
import re
from pathlib import Path
import subprocess
import sys
import traceback

# ---- Paths resolved relative to this file ----
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "datascribe_demo.db"        # created by the seeding script
SEED_PATH = BASE_DIR / "seed_test_data.py"

app = FastAPI(title="DataScribe Agent")


class NLQuery(BaseModel):
    question: str  # e.g., "Total revenue by sku for February 2025, highest first"


SQL_SYS = """Translate natural-language questions to valid SQLite SQL.
Rules:
- Use table: sales(day TEXT, sku TEXT, qty INT, price REAL)
- Return a single SELECT query only (no semicolons, no DDL/DML).
- Prefer readable column aliases.
"""


# -------------------- DB seeding helpers --------------------
def _db_needs_seed() -> bool:
    """Return True if the database doesn't exist, lacks the sales table, or is empty."""
    if not DB_PATH.exists():
        return True
    con = sqlite3.connect(str(DB_PATH))
    try:
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales'")
        if cur.fetchone() is None:
            return True
        cur.execute("SELECT COUNT(*) FROM sales")
        (n,) = cur.fetchone()
        return n == 0
    except Exception:
        # Any unexpected issue -> reseed
        return True
    finally:
        con.close()


def ensure_db():
    """
    Ensure the demo DB exists and is populated by invoking seed_test_data.py.
    Keeps the seed logic in a single source of truth (the script).
    """
    if _db_needs_seed():
        subprocess.run([sys.executable, str(SEED_PATH)], cwd=str(BASE_DIR), check=True)


@app.on_event("startup")
def _startup():
    ensure_db()


# -------------------- Utilities --------------------
def _sanitize_sql(raw: str) -> str:
    """Normalize likely LLM output into a single plain SELECT statement."""
    s = (raw or "").strip()

    # Strip ```sql ... ``` or ``` ... ```
    if s.startswith("```"):
        s = re.sub(r"^```(?:sql)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)

    # Remove leading "SQL:" label if present
    s = re.sub(r"^\s*SQL\s*:\s*", "", s, flags=re.IGNORECASE).strip()

    # If there are multiple statements separated by semicolons, keep only the first
    if ";" in s:
        s = s.split(";", 1)[0].strip()

    return s


def _execute_sql(sql: str) -> list[dict]:
    con = sqlite3.connect(str(DB_PATH))
    try:
        df = pd.read_sql_query(sql, con)
        return df.to_dict(orient="records")
    finally:
        con.close()


# -------------------- API --------------------
@app.post("/query")
def query(nl: NLQuery):
    """
    Convert NL to SQL and run it against SQLite demo DB.
    """
    ensure_db()  # defensive (also done on startup)

    question = (nl.question or "").strip()

    # 1) Call LLM (no fallback).
    try:
        raw_model_sql = complete(f"Question:\n{question}\nReturn only SQL:", SQL_SYS)
    except Exception as e:
        # Distinguish LLM/request errors from SQL/runtime errors.
        raise HTTPException(
            status_code=502,
            detail={
                "message": "LLM request failed.",
                "exception": f"{e.__class__.__name__}: {e}",
                "hint": "Check OPENAI_API_KEY, model availability, org/project, and billing/quota.",
            },
        )

    raw_model_sql = (raw_model_sql or "").strip()

    # 2) Handle fenced code and normalize typical LLM formatting
    sanitized_sql = raw_model_sql
    if "```" in sanitized_sql:
        candidates = [p for p in sanitized_sql.split("```") if "select" in p.lower()]
        if candidates:
            sanitized_sql = candidates[0].strip()

    sanitized_sql = _sanitize_sql(sanitized_sql)

    # 3) Guardrails: require SELECT and block DDL/DML keywords
    lowered = sanitized_sql.lower()
    if not re.match(r"^\s*select\b", lowered):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Only SELECT queries are allowed.",
                "raw_model_sql": raw_model_sql,
                "sanitized_sql": sanitized_sql,
                "hint": "Tune the system prompt or rephrase the question to elicit a SELECT.",
            },
        )

    if any(word in lowered for word in ["insert", "update", "delete", "drop", "create", "alter", "truncate"]):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Refusing non-SELECT SQL for safety.",
                "raw_model_sql": raw_model_sql,
                "sanitized_sql": sanitized_sql,
            },
        )

    # 4) Execute SQL and return rows (verbose errors on failure)
    try:
        rows = _execute_sql(sanitized_sql)
        return {"sql": sanitized_sql, "rows": rows}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "SQL execution failed.",
                "raw_model_sql": raw_model_sql,
                "sanitized_sql_tried": sanitized_sql,
                "exception": f"{e.__class__.__name__}: {str(e)}",
                "traceback": traceback.format_exc(),
                "db_path": str(DB_PATH),
                "hint": "Inspect the sanitized_sql and confirm the schema: sales(day TEXT, sku TEXT, qty INT, price REAL).",
            },
        )

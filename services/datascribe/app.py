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

DB_PATH = "datascribe_demo.db"  # created by the seeding script
app = FastAPI(title="DataScribe Agent")


class NLQuery(BaseModel):
    question: str  # e.g., "Total revenue by sku for February 2025, highest first"


SQL_SYS = """Translate natural-language questions to valid SQLite SQL.
Rules:
- Use table: sales(day TEXT, sku TEXT, qty INT, price REAL)
- Return a single SELECT query only (no semicolons, no DDL/DML).
- Prefer readable column aliases.
"""


def _sanitize_sql(raw: str) -> str:
    """Normalize likely LLM output into a single plain SELECT statement."""
    s = (raw or "").strip()

    # Strip ```sql ... ``` or ``` ... ```
    if s.startswith("```"):
        s = re.sub(r"^```(?:sql)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)

    # Remove leading "SQL:" label if present
    s = re.sub(r"^\s*SQL\s*:\s*", "", s, flags=re.IGNORECASE).strip()

    # Keep only the first statement (drop trailing prose or extra statements)
    if ";" in s:
        s = s.split(";", 1)[0].strip()

    return s


@app.post("/query")
def query(nl: NLQuery):
    """
    Convert NL to SQL and run it against SQLite demo DB.
    """
    # Ask the LLM for ONLY an SQL SELECT statement
    sql = complete(f"Question:\n{nl.question}\nReturn only SQL:", SQL_SYS).strip()

    # Handle fenced code and normalize typical LLM formatting
    if "```" in sql:
        candidates = [p for p in sql.split("```") if "select" in p.lower()]
        if candidates:
            sql = candidates[0].strip()

    # Extra normalization/sanitization
    sql = _sanitize_sql(sql)

    # Guardrail: only allow SELECTs; reject DDL/DML keywords
    lowered = sql.lower()
    if not re.match(r"^\s*select\b", lowered):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")
    if any(word in lowered for word in ["insert", "update", "delete", "drop", "create", "alter"]):
        raise HTTPException(status_code=400, detail="Refusing non-SELECT SQL for safety.")

    # Execute SQL and return rows
    con = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql, con)
        return {"sql": sql, "rows": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL error: {e}")
    finally:
        con.close()


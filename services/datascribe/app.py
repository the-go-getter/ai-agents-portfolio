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


@app.post("/query")
def query(nl: NLQuery):
    """
    Convert NL to SQL and run it against SQLite demo DB.
    """
    # Ask the LLM for ONLY an SQL SELECT statement
    sql = complete(f"Question:\n{nl.question}\nReturn only SQL:", SQL_SYS).strip()

    # Handle fenced code from the model if present
    if "```" in sql:
        # Keep the code portion that contains 'select'
        candidates = [p for p in sql.split("```") if "select" in p.lower()]
        if candidates:
            sql = candidates[0].strip()

    # Guardrail: block anything suspicious (very basic check)
    lowered = sql.lower()
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

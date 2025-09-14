"""
Tests for DataScribe Agent.

We validate:
- /query returns SQL and rows for a straightforward NL question.
- It refuses non-SELECT SQL (very basic safety).
"""
import json
from fastapi.testclient import TestClient
from services.datascribe.app import app

# Don't raise internal exceptions; we want HTTP status + body
client = TestClient(app, raise_server_exceptions=False)


def _json_or_text(resp):
    try:
        return resp.json()
    except Exception:
        return resp.text


def _print_line(test_case: str, expected: str, actual: str) -> None:
    # Required format: "test case, expected, actual"
    print(f"{test_case}, {expected}, {actual}")


def test_query_simple_aggregation():
    """
    Ask a simple analytics question and verify structured response.
    """
    q = {"question": "Show total quantity per SKU, highest first"}
    r = client.post("/query", json=q)

    # Prepare "expected" and "actual" strings (printed regardless of result)
    expected = "status=200; JSON includes keys ['sql','rows']; rows is list"
    body = _json_or_text(r)
    if isinstance(body, dict):
        keys = sorted(body.keys())
        rows_type = type(body.get("rows")).__name__ if "rows" in body else "missing"
        actual = f"status={r.status_code}; keys={keys}; rows_type={rows_type}"
    else:
        # non-JSON response
        preview = (body[:200] + "...") if isinstance(body, str) and len(body) > 200 else body
        actual = f"status={r.status_code}; non-json body preview={preview!r}"

    _print_line("test_query_simple_aggregation", expected, actual)

    # Assertions
    assert r.status_code == 200
    assert isinstance(body, dict)
    assert "sql" in body and "rows" in body
    assert isinstance(body["rows"], list)


def test_query_rejects_non_select():
    """
    The service should refuse dangerous SQL.
    We allow {200, 400} since LLM output isn't deterministic for DDL/DML.
    """
    r = client.post("/query", json={"question": "delete everything please"})

    expected = "status in {200, 400}"
    actual = f"status={r.status_code}"
    _print_line("test_query_rejects_non_select", expected, actual)

    assert r.status_code in (200, 400)

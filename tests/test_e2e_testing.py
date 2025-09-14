"""
Tests for E2E Testing Agent.

We validate:
- /generate creates a TS file string with key Playwright imports/keywords
- /run executes the Playwright runner (this test is optional and will be skipped
  automatically if Playwright is not installed)
"""
import os
import shutil
import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
from services.e2e_testing.app import app, TESTS_DIR

client = TestClient(app)


def test_generate_creates_ts_content(tmp_path):
    """
    Given an NL spec, we should generate a TS test with the right structure.
    """
    payload = {"spec": "Open https://example.com and assert title contains 'Example'"}
    r = client.post("/generate", json=payload)
    assert r.status_code == 200
    out = r.json()
    assert "file" in out
    # The file should exist
    assert os.path.exists(out["file"])
    # The generated file should contain basic Playwright patterns
    content = open(out["file"], "r", encoding="utf-8").read().lower()
    assert "import { test, expect } from '@playwright/test'".lower() in content
    assert "test.describe" in content
    assert "test(" in content
    assert "expect(" in content


@pytest.mark.skipif(shutil.which("npx") is None, reason="Node/Playwright not installed")
def test_run_executes_playwright():
    """
    Optional: actually run Playwright tests (headless). Requires Node + @playwright/test.
    """
    r = client.post("/run")
    assert r.status_code == 200
    body = r.json()
    # Exit code 0 means success; non-zero can still occur if the generated test fails.
    assert "exit_code" in body
    assert "stdout_tail" in body

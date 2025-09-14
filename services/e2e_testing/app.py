"""
E2E Testing Agent
=================
Turns a natural-language test idea into a Playwright Test (TypeScript) file,
then lets you run it headless via Playwright runner.

Endpoints:
- POST /generate  -> NL spec -> TS test file
- POST /run       -> executes tests (returns summary)
"""
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import pathlib
from common.llm_utils import complete

app = FastAPI(title="E2E Testing Agent")

# Where generated tests will be written
TESTS_DIR = pathlib.Path(__file__).parent / "tests"
TESTS_DIR.mkdir(parents=True, exist_ok=True)


class NLTest(BaseModel):
    spec: str  # e.g., "Open example.com and assert title contains 'Example'"


@app.post("/generate")
def generate_test(nl: NLTest):
    """
    Generate a TypeScript Playwright test from natural-language instructions.
    """
    system = "You generate Playwright Test (TypeScript) using @playwright/test."
    prompt = f"""
Write ONE Playwright test file in TypeScript with these rules:
- Include: import {{ test, expect }} from '@playwright/test';
- Use test.describe(...) and test('name', async ({{ page }}) => {{ ... }});
- Include at least one expect(...).
Natural-language spec:
{nl.spec}

Return ONLY the file content. No explanations.
"""
    ts_code = complete(prompt, system)

    # Save to a fixed file name for simplicity
    spec_path = TESTS_DIR / "generated.spec.ts"
    spec_path.write_text(ts_code, encoding="utf-8")
    return {"status": "ok", "file": str(spec_path)}


@app.post("/run")
def run_tests():
    """
    Run Playwright tests and return the output. Requires Node + @playwright/test installed.
    """
    try:
        # "-c services/e2e-testing" tells Playwright to use the local config in this folder
        result = subprocess.run(
            ["npx", "playwright", "test", "-c", str(pathlib.Path(__file__).parent)],
            capture_output=True, text=True, shell=True
        )
        return {
            "exit_code": result.returncode,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-2000:]
        }
    except Exception as e:
        return {"error": str(e)}

# AI-agents-portfolio

A compact portfolio demonstrating **agentic AI** patterns with production-friendly wrappers:

1) **Weather Emergency Agent** – fetches weather data and generates an ops-ready risk/response plan.
2) **DataScribe** – translates NL questions into SQL over SQLite and returns results.
3) **E2E Testing Agent** – turns NL specs into Playwright tests and executes them (CI/CD friendly).

## Quickstart 
```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
```

---
# Run the agents locally

Below are **PowerShell** and **curl** examples you can paste into your terminal to exercise each agent.

---

## Weather Emergency Agent (port `8002`)

### PowerShell
```powershell
$body = @{ lat = "17.3850"; lon = "78.4867" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8002/assess" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 20
```

### curl
```bash
curl -s -X POST "http://127.0.0.1:8002/assess"   -H "Content-Type: application/json"   -d '{"lat":"17.3850","lon":"78.4867"}'
```

---

## DataScribe (NL→SQL) Agent (port `8001`)

### PowerShell
```powershell
$body = @{ question = "Total revenue by SKU for February 2025, highest first" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8001/query" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 20
```

### curl
```bash
curl -s -X POST "http://127.0.0.1:8001/query"   -H "Content-Type: application/json"   -d '{"question":"Total revenue by SKU for February 2025, highest first"}'
```

---

## E2E Testing Agent (port `8000`)

### PowerShell
```powershell
# Generate a test from a natural-language spec
$genBody = @{  spec = "Open https://www.cvinayreddy.com and assert title contains 'portfolio'" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/generate" `
  -Method POST `
  -ContentType "application/json" `
  -Body $genBody | ConvertTo-Json -Depth 20

# Run the generated test
Invoke-RestMethod -Uri "http://127.0.0.1:8000/run" -Method POST | ConvertTo-Json -Depth 20
```

### curl
```bash
# Generate a test from a natural-language spec
curl -s -X POST "http://127.0.0.1:8000/generate"   -H "Content-Type: application/json"   -d '{"spec":"Open https://www.cvinayreddy.com and assert title contains '''portfolio'''"}'

# Run the generated test
curl -s -X POST "http://127.0.0.1:8000/run"
```

---

### Notes
- Ensure each service is running on the ports shown above (e.g., `uvicorn services.weather_emergency.app:app --port 8002`).
- PowerShell examples pipe to `ConvertTo-Json -Depth 20` to display the **full** JSON response without truncation.
                                            

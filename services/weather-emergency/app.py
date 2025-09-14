"""
Weather Emergency Agent
=======================
Fetches current/near-future weather metrics (Open-Meteo) and asks the LLM
to produce a risk level + concise operational response checklist.

Endpoint:
- POST /assess  -> { lat, lon } -> { metrics, plan }
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from common.llm_utils import complete
import requests

app = FastAPI(title="Weather Emergency Agent")
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"


class Location(BaseModel):
    lat: float
    lon: float


@app.post("/assess")
def assess(loc: Location):
    """
    Get weather metrics and ask the LLM for a response plan.
    """
    try:
        r = requests.get(OPEN_METEO, params={
            "latitude": loc.lat, "longitude": loc.lon,
            "hourly": "temperature_2m,wind_speed_10m,precipitation_probability",
            "current_weather": True
        }, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {e}")

    # Small, readable summary for the prompt (keep it deterministic)
    summary = {
        "tempC": data.get("current_weather", {}).get("temperature"),
        "wind": data.get("current_weather", {}).get("windspeed"),
        "precipProb": (data.get("hourly", {}).get("precipitation_probability") or [0])[0]
    }

    prompt = f"""Given weather metrics {summary}, produce:
- Risk level (Low/Medium/High) on a single line as 'Risk: <level>'.
- A concise 5-step response checklist for operations (numbered 1-5).
- If High, include a <=200 char SMS/email alert text labeled 'ALERT:' on the last line."""
    plan = complete(prompt, "You write concise, operations-focused incident responses.")
    return {"metrics": summary, "plan": plan}

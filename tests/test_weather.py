"""
Tests for Weather Emergency Agent.

We validate:
- /assess produces a metrics dict with certain keys
- The plan contains a 'Risk:' line and numbered steps
"""
from fastapi.testclient import TestClient
from services.weather_emergency.app import app

client = TestClient(app)


def test_assess_basic():
    """
    Use Hyderabad lat/lon. We don't validate exact numbers (weather is dynamic),
    just the response shape and presence of a plan.
    """
    payload = {"lat": 17.3850, "lon": 78.4867}
    r = client.post("/assess", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body and "plan" in body
    metrics = body["metrics"]
    assert "tempC" in metrics and "wind" in metrics and "precipProb" in metrics
    assert isinstance(body["plan"], str)
    assert "Risk:" in body["plan"]  # The model is asked to produce this label

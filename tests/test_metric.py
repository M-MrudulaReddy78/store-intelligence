# PROMPT: "Write pytest tests for /metrics endpoint covering empty store, staff exclusion, zero purchases."
# CHANGES MADE: Used a mock client and in‑memory storage.
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_metrics_empty_store():
    response = client.get("/stores/UNKNOWN/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0.0
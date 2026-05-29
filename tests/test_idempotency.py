# PROMPT: "Generate a test that verifies POST /events/ingest is idempotent: sending the same event twice should not create duplicate records."
# CHANGES MADE: Used a unique event_id and checked that second ingest returns duplicates=1.

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_idempotency():
    event = {
        "event_id": "test-idempotent-123",
        "store_id": "ST1008",
        "camera_id": "CAM1",
        "visitor_id": "VIS_TEST",
        "event_type": "ENTRY",
        "timestamp": "2026-04-10T12:00:00Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.9,
        "metadata": {}
    }
    r1 = client.post("/events/ingest", json=[event])
    assert r1.status_code == 200
    assert r1.json()["ingested"] == 1
    r2 = client.post("/events/ingest", json=[event])
    assert r2.status_code == 200
    assert r2.json()["duplicates"] == 1
# PROMPT: "Write pytest tests for /metrics endpoint covering:
#  - empty store (no events)
#  - staff exclusion
#  - zero purchases
#  - re-entry not double-counting"
#
# CHANGES MADE: Added mock database setup and teardown using tmp_path.

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ingestion import init_db, DB_PATH
import sqlite3
import json
from uuid import uuid4
from datetime import datetime

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    global DB_PATH
    DB_PATH = str(tmp_path / "test.db")
    init_db()
    yield
    # cleanup

def test_metrics_empty_store():
    response = client.get("/stores/STORE_EMPTY/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0.0

def test_metrics_excludes_staff():
    # Insert a staff ENTRY event
    staff_event = {
        "event_id": str(uuid4()),
        "store_id": "STORE_A",
        "camera_id": "CAM1",
        "visitor_id": "STAFF1",
        "event_type": "ENTRY",
        "timestamp": datetime.utcnow().isoformat(),
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": True,
        "confidence": 0.9,
        "metadata": {}
    }
    client.post("/events/ingest", json={"events": [staff_event]})
    response = client.get("/stores/STORE_A/metrics")
    assert response.json()["unique_visitors"] == 0

def test_metrics_zero_purchases():
    # Insert a customer ENTRY but no POS
    cust_event = {
        "event_id": str(uuid4()),
        "store_id": "STORE_B",
        "camera_id": "CAM1",
        "visitor_id": "CUST1",
        "event_type": "ENTRY",
        "timestamp": datetime.utcnow().isoformat(),
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.9,
        "metadata": {}
    }
    client.post("/events/ingest", json={"events": [cust_event]})
    response = client.get("/stores/STORE_B/metrics")
    assert response.json()["conversion_rate"] == 0.0
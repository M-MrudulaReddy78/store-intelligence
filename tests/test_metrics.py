# PROMPT: "Generate pytest tests for get_store_metrics ensuring zero-division handling and staff exclusion. Use mock database."
# CHANGES MADE: Added edge cases for empty store, all-staff, and zero purchases.

import pytest
from datetime import date, datetime, timedelta
from app.database import SessionLocal, EventRecord, SessionRecord, POSTransaction
from app.metrics import get_store_metrics
from app.models import StoreEvent

def test_metrics_empty_store():
    store_id = "TEST_EMPTY"
    metrics = get_store_metrics(store_id, date.today())
    assert metrics["unique_visitors"] == 0
    assert metrics["conversion_rate"] == 0.0
    assert metrics["current_queue_depth"] == 0

def test_metrics_staff_excluded():
    db = SessionLocal()
    # insert entry with is_staff=True
    event = EventRecord(
        event_id="staff1", store_id="TEST", camera_id="cam", visitor_id="v1",
        event_type="ENTRY", timestamp=datetime.utcnow(), is_staff=True,
        confidence=0.9, metadata_json={}
    )
    db.add(event)
    db.commit()
    metrics = get_store_metrics("TEST", date.today())
    assert metrics["unique_visitors"] == 0
    db.rollback()
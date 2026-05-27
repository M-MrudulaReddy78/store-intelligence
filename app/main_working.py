from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

app = FastAPI()

# In-memory storage
events_db = []

class Event(BaseModel):
    event_id: UUID
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: datetime
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float
    metadata: Dict[str, Any] = {}

class IngestRequest(BaseModel):
    events: List[Event]

@app.post("/events/ingest")
async def ingest(payload: IngestRequest):
    inserted = 0
    for ev in payload.events:
        # check for duplicates by event_id
        if not any(e.event_id == ev.event_id for e in events_db):
            events_db.append(ev)
            inserted += 1
    return {"status": "accepted", "inserted": inserted, "duplicates": len(payload.events)-inserted}

@app.get("/stores/{store_id}/metrics")
async def metrics(store_id: str):
    # Filter events for this store, exclude staff
    store_events = [e for e in events_db if e.store_id == store_id and not e.is_staff]
    unique_visitors = len(set(e.visitor_id for e in store_events if e.event_type in ("ENTRY", "REENTRY")))
    # For simplicity, conversion rate is 0 (no POS data)
    return {
        "unique_visitors": unique_visitors,
        "conversion_rate": 0.0,
        "avg_dwell_per_zone_ms": {},
        "queue_depth": 0,
        "abandonment_rate": 0.0
    }

@app.get("/stores/{store_id}/funnel")
async def funnel(store_id: str):
    # Simplified funnel
    store_events = [e for e in events_db if e.store_id == store_id and not e.is_staff]
    sessions = {e.visitor_id for e in store_events if e.event_type in ("ENTRY", "REENTRY")}
    total = len(sessions)
    return {
        "total_sessions": total,
        "entry": total,
        "zone_visit": 0,
        "billing_queue": 0,
        "purchase": 0,
        "dropoff_percentage": {"entry_to_zone": 0, "zone_to_billing": 0, "billing_to_purchase": 0}
    }

@app.get("/stores/{store_id}/anomalies")
async def anomalies(store_id: str):
    return []

@app.get("/health")
async def health():
    return {"status": "ok", "last_event_timestamp": None, "stale_feed_warning": False}
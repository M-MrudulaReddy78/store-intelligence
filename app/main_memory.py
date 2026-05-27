from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

app = FastAPI()

# In‑memory storage
events_db = []   # list of events

# ---------- Models ----------
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

# ---------- Endpoints ----------
@app.post("/events/ingest")
async def ingest(payload: IngestRequest):
    inserted = 0
    for ev in payload.events:
        # simple deduplication by event_id (string compare)
        if any(e['event_id'] == str(ev.event_id) for e in events_db):
            continue
        events_db.append(ev.dict())
        inserted += 1
    return {"status": "accepted", "inserted": inserted, "duplicates": len(payload.events)-inserted}

@app.get("/stores/{store_id}/metrics")
async def metrics(store_id: str):
    # Count unique visitors (non‑staff)
    unique = set()
    for ev in events_db:
        if ev['store_id'] == store_id and not ev['is_staff'] and ev['event_type'] in ('ENTRY','REENTRY'):
            unique.add(ev['visitor_id'])
    return {
        "unique_visitors": len(unique),
        "conversion_rate": 0.0,
        "avg_dwell_per_zone_ms": {},
        "queue_depth": 0,
        "abandonment_rate": 0.0
    }

@app.get("/health")
async def health():
    return {"status": "ok", "last_event_timestamp": None, "stale_feed_warning": False}
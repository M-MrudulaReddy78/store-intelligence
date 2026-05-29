from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from .models import StoreEvent
from .ingestion import ingest_events
from .metrics import get_store_metrics
from .funnel import get_funnel
from .anomalies import detect_anomalies
from .health import get_health_status
from .database import SessionLocal, EventRecord
from .pos_loader import load_pos_transactions
import logging
import uuid

app = FastAPI(title="Store Intelligence API")

# Setup structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("store-intel")

@app.on_event("startup")
def startup():
    load_pos_transactions("data/Brigade_Bangalore_10_April_26 (1).csv")

@app.post("/events/ingest")
async def ingest(events: List[StoreEvent]):
    trace_id = str(uuid.uuid4())
    logger.info(f"trace_id={trace_id} endpoint=/events/ingest event_count={len(events)}")
    result = ingest_events(events)
    logger.info(f"trace_id={trace_id} ingested={result['ingested']} duplicates={result['duplicates']}")
    return result

@app.get("/stores/{store_id}/metrics")
async def metrics(store_id: str, date: Optional[date] = None):
    if date is None:
        date = datetime.utcnow().date()
    try:
        return get_store_metrics(store_id, date)
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

@app.get("/stores/{store_id}/funnel")
async def funnel(store_id: str, date: Optional[date] = None):
    if date is None:
        date = datetime.utcnow().date()
    return get_funnel(store_id, date)

@app.get("/stores/{store_id}/anomalies")
async def anomalies(store_id: str):
    return detect_anomalies(store_id)

@app.get("/health")
async def health():
    return get_health_status()
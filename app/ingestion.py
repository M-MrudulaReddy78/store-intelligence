from .database import SessionLocal, EventRecord, SessionRecord
from .models import StoreEvent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def ingest_events(events: list[StoreEvent]) -> dict:
    db = SessionLocal()
    ingested = 0
    duplicates = 0
    errors = []

    for event in events:
        existing = db.query(EventRecord).filter(EventRecord.event_id == event.event_id).first()
        if existing:
            duplicates += 1
            continue
        try:
            record = EventRecord(
                event_id=event.event_id,
                store_id=event.store_id,
                camera_id=event.camera_id,
                visitor_id=event.visitor_id,
                event_type=event.event_type,
                timestamp=event.timestamp,
                zone_id=event.zone_id,
                dwell_ms=event.dwell_ms,
                is_staff=event.is_staff,
                confidence=event.confidence,
                metadata_json=event.metadata.dict() if event.metadata else {}
            )
            db.add(record)
            ingested += 1
        except Exception as e:
            errors.append({"event_id": event.event_id, "error": str(e)})

    db.commit()
    db.close()
    return {"ingested": ingested, "duplicates": duplicates, "errors": errors}
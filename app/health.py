from datetime import datetime, timedelta
from .database import SessionLocal, EventRecord

def get_health_status():
    db = SessionLocal()
    latest_per_store = {}
    stores = db.query(EventRecord.store_id).distinct().all()
    for (store_id,) in stores:
        latest = db.query(EventRecord.timestamp).filter(EventRecord.store_id == store_id).order_by(EventRecord.timestamp.desc()).first()
        if latest:
            latest_per_store[store_id] = latest[0].isoformat()
    db.close()

    now = datetime.utcnow()
    stale_feeds = {}
    for store_id, last_ts in latest_per_store.items():
        last = datetime.fromisoformat(last_ts)
        if (now - last).total_seconds() > 600:  # 10 minutes lag
            stale_feeds[store_id] = f"Last event at {last_ts}"

    return {
        "status": "healthy" if not stale_feeds else "degraded",
        "last_event_timestamp_per_store": latest_per_store,
        "stale_feeds": stale_feeds
    }
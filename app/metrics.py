from sqlalchemy import func, and_
from datetime import datetime, timedelta
from .database import SessionLocal, EventRecord, SessionRecord, POSTransaction

def get_store_metrics(store_id: str, date: datetime.date):
    db = SessionLocal()
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())

    # Unique visitors (non-staff)
    unique_visitors = db.query(EventRecord.visitor_id).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= start,
        EventRecord.timestamp <= end,
        EventRecord.event_type == "ENTRY",
        EventRecord.is_staff == False
    ).distinct().count()

    # Conversion rate via POS correlation
    sessions = db.query(SessionRecord).filter(
        SessionRecord.store_id == store_id,
        SessionRecord.entry_time >= start,
        SessionRecord.entry_time <= end
    ).all()

    converted_sessions = sum(1 for s in sessions if s.converted)
    conversion_rate = (converted_sessions / unique_visitors) if unique_visitors > 0 else 0.0

    # Average dwell per zone (from ZONE_DWELL events)
    dwell_results = db.query(
        EventRecord.zone_id,
        func.avg(EventRecord.dwell_ms).label("avg_dwell")
    ).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= start,
        EventRecord.timestamp <= end,
        EventRecord.event_type == "ZONE_DWELL",
        EventRecord.is_staff == False
    ).group_by(EventRecord.zone_id).all()

    avg_dwell_per_zone = {zone: float(dwell) for zone, dwell in dwell_results}

    # Latest queue depth (from most recent BILLING_QUEUE_JOIN event)
    latest_queue = db.query(EventRecord).filter(
        EventRecord.store_id == store_id,
        EventRecord.event_type == "BILLING_QUEUE_JOIN",
        EventRecord.timestamp >= start
    ).order_by(EventRecord.timestamp.desc()).first()

    queue_depth = latest_queue.metadata_json.get("queue_depth", 0) if latest_queue else 0

    # Abandonment rate
    queue_joins = db.query(EventRecord).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= start,
        EventRecord.event_type == "BILLING_QUEUE_JOIN",
        EventRecord.is_staff == False
    ).count()

    abandonments = db.query(EventRecord).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= start,
        EventRecord.event_type == "BILLING_QUEUE_ABANDON",
        EventRecord.is_staff == False
    ).count()

    abandonment_rate = (abandonments / queue_joins) if queue_joins > 0 else 0.0

    db.close()
    return {
        "store_id": store_id,
        "date": date.isoformat(),
        "unique_visitors": unique_visitors,
        "conversion_rate": conversion_rate,
        "avg_dwell_ms_per_zone": avg_dwell_per_zone,
        "current_queue_depth": queue_depth,
        "abandonment_rate": abandonment_rate
    }
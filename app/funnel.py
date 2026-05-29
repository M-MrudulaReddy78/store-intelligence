from sqlalchemy import and_
from datetime import datetime, timedelta
from .database import SessionLocal, EventRecord

def get_funnel(store_id: str, date: datetime.date):
    db = SessionLocal()
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())

    # Get all visitor sessions (ENTRY events)
    entries = db.query(EventRecord.visitor_id).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= start,
        EventRecord.timestamp <= end,
        EventRecord.event_type == "ENTRY",
        EventRecord.is_staff == False
    ).distinct().all()
    total_visitors = len(entries)

    # Visitors who entered any zone (ZONE_ENTER)
    zone_visitors = db.query(EventRecord.visitor_id).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= start,
        EventRecord.timestamp <= end,
        EventRecord.event_type == "ZONE_ENTER",
        EventRecord.is_staff == False
    ).distinct().count()

    # Visitors who joined billing queue
    billing_visitors = db.query(EventRecord.visitor_id).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= start,
        EventRecord.timestamp <= end,
        EventRecord.event_type == "BILLING_QUEUE_JOIN",
        EventRecord.is_staff == False
    ).distinct().count()

    # Purchased visitors (via POS correlation, using session.converted flag)
    from .database import SessionRecord
    purchased_sessions = db.query(SessionRecord).filter(
        SessionRecord.store_id == store_id,
        SessionRecord.entry_time >= start,
        SessionRecord.entry_time <= end,
        SessionRecord.converted == True
    ).count()

    db.close()

    funnel_stages = [
        {"stage": "Entry", "count": total_visitors, "dropoff_rate": 0.0},
        {"stage": "Zone Visit", "count": zone_visitors, "dropoff_rate": (total_visitors - zone_visitors) / total_visitors if total_visitors else 0},
        {"stage": "Billing Queue", "count": billing_visitors, "dropoff_rate": (zone_visitors - billing_visitors) / zone_visitors if zone_visitors else 0},
        {"stage": "Purchase", "count": purchased_sessions, "dropoff_rate": (billing_visitors - purchased_sessions) / billing_visitors if billing_visitors else 0}
    ]

    return {"store_id": store_id, "date": date.isoformat(), "funnel": funnel_stages}
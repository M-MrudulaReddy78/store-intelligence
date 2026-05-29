from datetime import datetime, timedelta
from sqlalchemy import func, and_
from .database import SessionLocal, EventRecord

def detect_anomalies(store_id: str):
    db = SessionLocal()
    now = datetime.utcnow()
    anomalies = []

    # 1. Queue spike (current queue depth > 2 * historical 7-day avg)
    week_ago = now - timedelta(days=7)
    avg_queue = db.query(func.avg(EventRecord.metadata_json["queue_depth"].astext.cast(float))).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= week_ago,
        EventRecord.event_type == "BILLING_QUEUE_JOIN"
    ).scalar() or 0

    current_queue = db.query(EventRecord).filter(
        EventRecord.store_id == store_id,
        EventRecord.event_type == "BILLING_QUEUE_JOIN",
        EventRecord.timestamp >= now - timedelta(minutes=10)
    ).order_by(EventRecord.timestamp.desc()).first()

    if current_queue and current_queue.metadata_json.get("queue_depth", 0) > avg_queue * 2:
        anomalies.append({
            "type": "QUEUE_SPIKE",
            "severity": "WARN",
            "description": f"Queue depth {current_queue.metadata_json['queue_depth']} exceeds 2x weekly avg {avg_queue:.1f}",
            "suggested_action": "Open additional billing counter"
        })

    # 2. Conversion drop (conversion rate < 50% of 7-day avg)
    # Requires metrics function; simplified here
    from .metrics import get_store_metrics
    today_metrics = get_store_metrics(store_id, now.date())
    last_week_conv = []
    for i in range(1, 8):
        day = (now - timedelta(days=i)).date()
        metrics = get_store_metrics(store_id, day)
        last_week_conv.append(metrics["conversion_rate"])
    avg_conv = sum(last_week_conv) / len(last_week_conv) if last_week_conv else 0
    if avg_conv > 0 and today_metrics["conversion_rate"] < avg_conv * 0.5:
        anomalies.append({
            "type": "CONVERSION_DROP",
            "severity": "CRITICAL",
            "description": f"Today's conversion {today_metrics['conversion_rate']:.2%} is <50% of weekly avg {avg_conv:.2%}",
            "suggested_action": "Check staff performance, promotions, or product availability"
        })

    # 3. Dead zone (no zone visits in last 30 mins)
    last_30min = now - timedelta(minutes=30)
    zone_activity = db.query(EventRecord).filter(
        EventRecord.store_id == store_id,
        EventRecord.timestamp >= last_30min,
        EventRecord.event_type.in_(["ZONE_ENTER", "ZONE_DWELL"])
    ).first()
    if not zone_activity:
        anomalies.append({
            "type": "DEAD_ZONE",
            "severity": "INFO",
            "description": "No customer movement detected in any zone for 30 minutes",
            "suggested_action": "Check camera feed or store opening hours"
        })

    db.close()
    return anomalies
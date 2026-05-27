import sqlite3
from .ingestion import DB_PATH
from .metrics import get_metrics
from datetime import datetime, timedelta

def get_anomalies(store_id: str):
    anomalies = []
    with sqlite3.connect(DB_PATH) as conn:
        # Queue spike: queue depth > 5
        metrics = get_metrics(store_id)
        if metrics["queue_depth"] > 5:
            anomalies.append({
                "type": "BILLING_QUEUE_SPIKE",
                "severity": "WARN",
                "description": f"Queue depth is {metrics['queue_depth']} (>5)",
                "suggested_action": "Open additional billing counters"
            })

        # Conversion drop vs 7-day avg
        # For simplicity, we compare today's conversion with previous 7 days.
        # Need to compute daily conversion. We'll do a quick SQL.
        cur = conn.execute("""
            SELECT DATE(timestamp) as day,
                   COUNT(DISTINCT CASE WHEN event_type IN ('ENTRY','REENTRY') THEN visitor_id END) as visitors,
                   COUNT(DISTINCT CASE WHEN event_type = 'BILLING_QUEUE_JOIN' THEN visitor_id END) as conversions
            FROM events
            WHERE store_id = ? AND is_staff = 0
            GROUP BY day
            ORDER BY day DESC
            LIMIT 8
        """, (store_id,))
        rows = cur.fetchall()
        if len(rows) >= 2:
            today_conv = rows[0][2] / rows[0][1] if rows[0][1] else 0
            prev_week_conv = sum(r[2] for r in rows[1:]) / sum(r[1] for r in rows[1:]) if sum(r[1] for r in rows[1:]) else 0
            if prev_week_conv > 0 and today_conv < 0.5 * prev_week_conv:
                anomalies.append({
                    "type": "CONVERSION_DROP",
                    "severity": "CRITICAL",
                    "description": f"Today's conversion ({today_conv:.2%}) is <50% of 7-day avg ({prev_week_conv:.2%})",
                    "suggested_action": "Check for operational issues or competitor activity"
                })

        # Dead zone: no visits in last 30 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        cur = conn.execute("""
            SELECT COUNT(*) FROM events
            WHERE store_id = ? AND event_type IN ('ENTRY','REENTRY')
              AND timestamp > ?
        """, (store_id, cutoff.isoformat()))
        if cur.fetchone()[0] == 0:
            anomalies.append({
                "type": "DEAD_ZONE",
                "severity": "INFO",
                "description": "No visitor entry in last 30 minutes",
                "suggested_action": "Consider marketing or staff break"
            })

    return anomalies
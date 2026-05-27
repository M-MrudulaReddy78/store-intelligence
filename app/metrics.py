import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from .ingestion import DB_PATH

def get_metrics(store_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        # Unique visitors (non-staff)
        cur = conn.execute("""
            SELECT COUNT(DISTINCT visitor_id) FROM events
            WHERE store_id = ? AND is_staff = 0
              AND event_type IN ('ENTRY', 'REENTRY')
        """, (store_id,))
        unique_visitors = cur.fetchone()[0] or 0

        # Load POS transactions for this store
        # In production, you would have a separate POS table. Here we read CSV.
        pos_df = pd.read_csv("data/pos_transactions.csv", parse_dates=["timestamp"])
        pos_df = pos_df[pos_df["store_id"] == store_id]

        converted_visitors = set()
        # For each POS transaction, find visitors in billing zone within 5 min before
        for _, row in pos_df.iterrows():
            txn_time = row["timestamp"]
            start_window = txn_time - timedelta(minutes=5)
            cur2 = conn.execute("""
                SELECT DISTINCT visitor_id FROM events
                WHERE store_id = ? AND zone_id = 'BILLING'
                  AND event_type = 'ZONE_ENTER'
                  AND timestamp BETWEEN ? AND ?
                  AND is_staff = 0
            """, (store_id, start_window.isoformat(), txn_time.isoformat()))
            for (vid,) in cur2.fetchall():
                converted_visitors.add(vid)

        conversion_rate = len(converted_visitors) / unique_visitors if unique_visitors > 0 else 0.0

        # Average dwell per zone (non-staff)
        cur = conn.execute("""
            SELECT zone_id, AVG(dwell_ms) FROM events
            WHERE store_id = ? AND event_type = 'ZONE_DWELL' AND is_staff = 0
            GROUP BY zone_id
        """, (store_id,))
        avg_dwell = {row[0]: row[1] for row in cur.fetchall()}

        # Current queue depth (visitors currently in billing zone)
        cur = conn.execute("""
            SELECT COUNT(DISTINCT visitor_id) FROM events e1
            WHERE store_id = ? AND zone_id = 'BILLING'
              AND NOT EXISTS (
                SELECT 1 FROM events e2
                WHERE e2.visitor_id = e1.visitor_id
                  AND e2.zone_id = 'BILLING'
                  AND e2.event_type = 'ZONE_EXIT'
                  AND e2.timestamp > e1.timestamp
              )
        """, (store_id,))
        queue_depth = cur.fetchone()[0] or 0

        # Abandonment rate: visitors who entered billing but left without purchase
        cur = conn.execute("""
            SELECT COUNT(DISTINCT visitor_id) FROM events
            WHERE store_id = ? AND event_type = 'BILLING_QUEUE_ABANDON'
        """, (store_id,))
        abandoned = cur.fetchone()[0] or 0
        abandonment_rate = abandoned / unique_visitors if unique_visitors > 0 else 0.0

        return {
            "unique_visitors": unique_visitors,
            "conversion_rate": round(conversion_rate, 4),
            "avg_dwell_per_zone_ms": avg_dwell,
            "queue_depth": queue_depth,
            "abandonment_rate": round(abandonment_rate, 4)
        }
import sqlite3
from .ingestion import DB_PATH
from datetime import timedelta
import pandas as pd

def get_funnel(store_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        # Get all sessions: each unique visitor with first ENTRY/REENTRY
        cur = conn.execute("""
            SELECT visitor_id, MIN(timestamp) as session_start
            FROM events
            WHERE store_id = ? AND is_staff = 0
              AND event_type IN ('ENTRY', 'REENTRY')
            GROUP BY visitor_id
        """, (store_id,))
        sessions = cur.fetchall()
        total_sessions = len(sessions)

        # Load POS transactions
        pos_df = pd.read_csv("data/pos_transactions.csv", parse_dates=["timestamp"])
        pos_df = pos_df[pos_df["store_id"] == store_id]

        # Stage counts
        zone_visit = 0
        billing_queue = 0
        purchase = 0

        for visitor_id, session_start in sessions:
            # Check if visitor entered any zone (non-entry/exit)
            cur2 = conn.execute("""
                SELECT 1 FROM events
                WHERE visitor_id = ? AND event_type = 'ZONE_ENTER'
                LIMIT 1
            """, (visitor_id,))
            if cur2.fetchone():
                zone_visit += 1

            # Check if entered billing zone
            cur2 = conn.execute("""
                SELECT 1 FROM events
                WHERE visitor_id = ? AND zone_id = 'BILLING'
                LIMIT 1
            """, (visitor_id,))
            if cur2.fetchone():
                billing_queue += 1

            # Check if purchased (POS within session window)
            session_end = session_start + timedelta(hours=2)  # assume max session length 2h
            matched = pos_df[
                (pos_df["timestamp"] >= session_start) &
                (pos_df["timestamp"] <= session_end)
            ]
            if not matched.empty:
                purchase += 1

        # Drop-off percentages
        entry_to_zone = round((total_sessions - zone_visit) / total_sessions * 100, 2) if total_sessions else 0
        zone_to_billing = round((zone_visit - billing_queue) / zone_visit * 100, 2) if zone_visit else 0
        billing_to_purchase = round((billing_queue - purchase) / billing_queue * 100, 2) if billing_queue else 0

        return {
            "total_sessions": total_sessions,
            "entry": total_sessions,
            "zone_visit": zone_visit,
            "billing_queue": billing_queue,
            "purchase": purchase,
            "dropoff_percentage": {
                "entry_to_zone": entry_to_zone,
                "zone_to_billing": zone_to_billing,
                "billing_to_purchase": billing_to_purchase
            }
        }
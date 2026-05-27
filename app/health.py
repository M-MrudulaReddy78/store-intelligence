import sqlite3
from .ingestion import DB_PATH
from datetime import datetime, timedelta

def get_health():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT MAX(timestamp) FROM events")
        last_ts_str = cur.fetchone()[0]
    if last_ts_str is None:
        last_ts = None
        stale = False
    else:
        last_ts = datetime.fromisoformat(last_ts_str)
        stale = (datetime.utcnow() - last_ts) > timedelta(minutes=10)
    return {
        "status": "degraded" if stale else "ok",
        "last_event_timestamp": last_ts_str,
        "stale_feed_warning": stale
    }
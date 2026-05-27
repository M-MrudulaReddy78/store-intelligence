import sqlite3
import json
from .models import Event

DB_PATH = "store_intelligence.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                store_id TEXT,
                camera_id TEXT,
                visitor_id TEXT,
                event_type TEXT,
                timestamp TEXT,
                zone_id TEXT,
                dwell_ms INTEGER,
                is_staff INTEGER,
                confidence REAL,
                metadata TEXT
            )
        """)
        # Index for faster queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_store_time ON events(store_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_visitor ON events(visitor_id)")

def ingest_events(events: list[Event]) -> int:
    inserted = 0
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        for ev in events:
            try:
                cur.execute("""
                    INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    str(ev.event_id),
                    ev.store_id,
                    ev.camera_id,
                    ev.visitor_id,
                    ev.event_type,
                    ev.timestamp.isoformat(),
                    ev.zone_id,
                    ev.dwell_ms,
                    1 if ev.is_staff else 0,
                    ev.confidence,
                    json.dumps(ev.metadata)
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                # duplicate event_id -> skip
                continue
    return inserted
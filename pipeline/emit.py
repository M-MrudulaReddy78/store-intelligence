"""
Event emission module: sends structured events to the API endpoint.
Includes batching, retry logic, and offline fallback.
"""

import requests
import json
import time
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4
import logging

logger = logging.getLogger("event-emitter")

API_URL = "http://localhost:8000/events/ingest"
RETRY_COUNT = 3
RETRY_DELAY = 1  # seconds
BATCH_SIZE = 50  # send events in batches

class EventEmitter:
    def __init__(self, endpoint=API_URL):
        self.endpoint = endpoint
        self.buffer: List[Dict] = []
        self.session = requests.Session()

    def create_event(self, store_id: str, camera_id: str, visitor_id: str,
                     event_type: str, timestamp: datetime, zone_id: str = None,
                     dwell_ms: int = 0, is_staff: bool = False, confidence: float = 1.0,
                     metadata: Dict = None) -> Dict:
        """Build an event dictionary conforming to required schema."""
        return {
            "event_id": str(uuid4()),
            "store_id": store_id,
            "camera_id": camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": timestamp.isoformat() + "Z",
            "zone_id": zone_id,
            "dwell_ms": dwell_ms,
            "is_staff": is_staff,
            "confidence": confidence,
            "metadata": metadata or {}
        }

    def add_event(self, event: Dict):
        """Add event to buffer and flush if batch size reached."""
        self.buffer.append(event)
        if len(self.buffer) >= BATCH_SIZE:
            self.flush()

    def flush(self):
        """Send all buffered events to API with retries."""
        if not self.buffer:
            return
        events_to_send = self.buffer.copy()
        self.buffer.clear()

        for attempt in range(RETRY_COUNT):
            try:
                resp = self.session.post(self.endpoint, json=events_to_send, timeout=5)
                if resp.status_code == 200:
                    logger.info(f"Sent {len(events_to_send)} events, response: {resp.json()}")
                    return
                else:
                    logger.warning(f"API returned {resp.status_code}, retrying...")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}, attempt {attempt+1}")
            time.sleep(RETRY_DELAY)

        # If all retries fail, write to local file for offline debugging
        with open("failed_events.jsonl", "a") as f:
            for ev in events_to_send:
                f.write(json.dumps(ev) + "\n")
        logger.error(f"Failed to send {len(events_to_send)} events after {RETRY_COUNT} retries. Saved to failed_events.jsonl")

    def close(self):
        self.flush()
        self.session.close()

# Global emitter instance (for simple imports)
_emitter = None

def get_emitter():
    global _emitter
    if _emitter is None:
        _emitter = EventEmitter()
    return _emitter

def emit_event(**kwargs):
    """Convenience function to create and add one event."""
    emitter = get_emitter()
    event = emitter.create_event(**kwargs)
    emitter.add_event(event)
    return event["event_id"]
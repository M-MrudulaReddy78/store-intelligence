import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class EventEmitter:
    def __init__(self, store_id: str, camera_id: str):
        self.store_id = store_id
        self.camera_id = camera_id
        self._seq_counter = {}  # visitor_id -> last seq

    def create_event(self, visitor_id: str, event_type: str,
                     timestamp: datetime, zone_id: Optional[str] = None,
                     dwell_ms: int = 0, is_staff: bool = False,
                     confidence: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Increment session sequence
        seq = self._seq_counter.get(visitor_id, 0) + 1
        self._seq_counter[visitor_id] = seq

        event = {
            "event_id": str(uuid.uuid4()),
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": timestamp.isoformat() + "Z",
            "zone_id": zone_id,
            "dwell_ms": dwell_ms,
            "is_staff": is_staff,
            "confidence": confidence,
            "metadata": metadata or {}
        }
        event["metadata"]["session_seq"] = seq
        return event
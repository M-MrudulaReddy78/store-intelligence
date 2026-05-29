import cv2
import supervision as sv
from ultralytics import YOLO
from datetime import datetime, timezone
from uuid import uuid4
import requests

API_URL = "http://localhost:8000/events/ingest"
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture("data/CAM 1.mp4")
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1
    results = model(frame, conf=0.1, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(results)
    persons = detections[detections.class_id == 0]
    if len(persons) > 0:
        # Send one ENTRY event per frame (just for testing)
        event = {
            "event_id": str(uuid4()),
            "store_id": "ST1008",
            "camera_id": "CAM1",
            "visitor_id": str(uuid4()),
            "event_type": "ENTRY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.8,
            "metadata": {}
        }
        r = requests.post(API_URL, json=[event], timeout=2)
        if r.status_code == 200:
            print(f"Frame {frame_count}: sent ENTRY")
        else:
            print(f"Frame {frame_count}: failed {r.status_code}")
    if frame_count % 100 == 0:
        print(f"Processed {frame_count} frames")

cap.release()
print("Done")
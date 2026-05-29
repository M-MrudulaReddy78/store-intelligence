import cv2
import supervision as sv
from ultralytics import YOLO
from datetime import datetime, timedelta
from uuid import uuid4
import requests

API_URL = "http://localhost:8000/events/ingest"

def send_event(event):
    try:
        resp = requests.post(API_URL, json=[event], timeout=2)
        if resp.status_code == 200:
            print(f"✓ Sent ENTRY for {event['visitor_id']}")
        else:
            print(f"✗ Failed: {resp.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")

def process_video(video_path, store_id, camera_id):
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    start_time = datetime.utcnow()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        timestamp = start_time + timedelta(seconds=frame_count / fps)
        results = model(frame, conf=0.25, verbose=False)[0]  # lower confidence
        detections = sv.Detections.from_ultralytics(results)
        persons = detections[detections.class_id == 0]
        if len(persons) > 0:
            print(f"Frame {frame_count}: {len(persons)} person(s) detected")
            for _ in range(len(persons)):
                event = {
                    "event_id": str(uuid4()),
                    "store_id": store_id,
                    "camera_id": camera_id,
                    "visitor_id": str(uuid4()),
                    "event_type": "ENTRY",
                    "timestamp": timestamp.isoformat() + "Z",
                    "zone_id": None,
                    "dwell_ms": 0,
                    "is_staff": False,
                    "confidence": 0.8,
                    "metadata": {}
                }
                send_event(event)
        if frame_count % 100 == 0:
            print(f"Processed {frame_count} frames")
    cap.release()
    print("Done")

if __name__ == "__main__":
    process_video("data/CAM 1.mp4", "ST1008", "CAM_ENTRY_01")
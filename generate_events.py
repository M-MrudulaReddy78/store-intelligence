import sys
import json
import cv2
from ultralytics import YOLO
from datetime import datetime, timezone
from uuid import uuid4

video_path = "data/clips/camera1/CAM 1.mp4"
store_id = "STORE_001"
camera_id = "CAM1"

model = YOLO('yolov8n.pt', verbose=False)
cap = cv2.VideoCapture(video_path)
frame_count = 0
event_counter = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1
    if frame_count % 10 != 0:   # process every 10th frame to avoid too many events
        continue

    results = model(frame, classes=[0], conf=0.3, iou=0.5, verbose=False)
    if results[0].boxes is None:
        continue
    boxes = results[0].boxes.xyxy.cpu().numpy()
    confs = results[0].boxes.conf.cpu().numpy()
    timestamp = datetime.now(timezone.utc).isoformat() + "Z"

    for i, (box, conf) in enumerate(zip(boxes, confs)):
        event_counter += 1
        event = {
            "event_id": str(uuid4()),
            "store_id": store_id,
            "camera_id": camera_id,
            "visitor_id": f"VIS_{store_id}_{frame_count}_{i}",
            "event_type": "ENTRY",
            "timestamp": timestamp,
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": float(conf),
            "metadata": {}
        }
        sys.stdout.write(json.dumps(event) + "\n")
        sys.stdout.flush()
        print(f"Generated event {event_counter}", file=sys.stderr)

cap.release()
print(f"Done. Total frames processed: {frame_count}, events generated: {event_counter}", file=sys.stderr)
import sys
import json
import cv2
from ultralytics import YOLO
from datetime import datetime, timezone
from uuid import uuid4

if len(sys.argv) < 4:
    print("Usage: generate_events_args.py <video_path> <store_id> <camera_id> [step_frames=10] [max_frames=None]")
    sys.exit(1)

video_path = sys.argv[1]
store_id = sys.argv[2]
camera_id = sys.argv[3]
step_frames = int(sys.argv[4]) if len(sys.argv) > 4 else 10
max_frames = int(sys.argv[5]) if len(sys.argv) > 5 else None

model = YOLO('yolov8n.pt', verbose=False)
cap = cv2.VideoCapture(video_path)
frame_count = 0
event_counter = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1
    if frame_count % step_frames != 0:
        continue
    if max_frames and frame_count > max_frames:
        break

    results = model(frame, classes=[0], conf=0.3, iou=0.5, verbose=False)
    if results[0].boxes is None:
        continue
    boxes = results[0].boxes.xyxy.cpu().numpy()
    confs = results[0].boxes.conf.cpu().numpy()
    timestamp = datetime.now(timezone.utc).isoformat()
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

cap.release()
print(f"Done. Frames: {frame_count}, events: {event_counter}", file=sys.stderr)
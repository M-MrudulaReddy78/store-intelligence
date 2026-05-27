import sys
import json
import cv2
from ultralytics import YOLO
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from pipeline.emit import EventEmitter

video_path = "data/clips/camera1/CAM 1.mp4"
store_id = "STORE_001"
camera_id = "CAM1"
layout_path = "data/store_layout.json"  # unused

model = YOLO('yolov8n.pt', verbose=False)
cap = cv2.VideoCapture(video_path)
emitter = EventEmitter(store_id, camera_id)
frame_idx = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    if frame_idx % 30 != 0:
        continue  # only process every 30th frame to speed up
    timestamp = datetime.now(timezone.utc)
    results = model(frame, classes=[0], conf=0.3, iou=0.5, verbose=False)
    if results[0].boxes is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confs = results[0].boxes.conf.cpu().numpy()
        for i, (box, conf) in enumerate(zip(boxes, confs)):
            # Create a unique visitor ID per detection per frame (not tracked)
            visitor_id = f"VIS_{store_id}_{frame_idx}_{i}"
            event = emitter.create_event(visitor_id, "ENTRY", timestamp, is_staff=False, confidence=float(conf))
            sys.stdout.write(json.dumps(event) + "\n")
            sys.stdout.flush()
            print(f"EVENT: ENTRY {visitor_id}", file=sys.stderr)
cap.release()
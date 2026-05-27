import cv2
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
cap = cv2.VideoCapture("data/clips/camera1/CAM 1.mp4")
frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_count += 1
    if frame_count % 30 == 0:
        print(f"Frame {frame_count}")
    results = model(frame, classes=[0], conf=0.3, iou=0.5, verbose=False)
    if results[0].boxes is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        print(f"  Detected {len(boxes)} people")
        for box in boxes:
            center_y = (box[1] + box[3]) / 2
            print(f"    y = {center_y:.1f}")
    else:
        print("  No detections")
cap.release()
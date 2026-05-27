from ultralytics import YOLO
import cv2

# Load a pre-trained YOLOv8 model
model = YOLO("yolov8n.pt")

# Run inference on a video file
results = model('path/to/your/video.mp4', stream=True)

for result in results:
    # Access frames and detections
    frame = result.orig_img
    boxes = result.boxes

    # Count people (class ID 0 for COCO dataset)
    people_count = sum(1 for box in boxes if int(box.cls) == 0)

    # Display the count on the frame
    cv2.putText(frame, f'People Count: {people_count}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imshow("YOLO Counting", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
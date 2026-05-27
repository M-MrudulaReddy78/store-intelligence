
import sys
import json
import cv2
from ultralytics import YOLO
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

# Add parent dir to path for imports (when running as script)
sys.path.append(str(Path(__file__).parent.parent))
from pipeline.emit import EventEmitter

# -------------------------------------------------------------------
# Helper: simple staff detection based on red uniform colour
# -------------------------------------------------------------------
def is_staff_red_uniform(bbox, frame):
    x1, y1, x2, y2 = map(int, bbox)
    # Upper half of the bounding box (chest area)
    roi = frame[y1:y1+(y2-y1)//2, x1:x2]
    if roi.size == 0:
        return False
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # Red hue range (0-10 and 170-180)
    mask1 = cv2.inRange(hsv, (0, 50, 50), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (170, 50, 50), (180, 255, 255))
    red_mask = cv2.bitwise_or(mask1, mask2)
    red_ratio = cv2.countNonZero(red_mask) / (roi.shape[0] * roi.shape[1])
    return red_ratio > 0.3   # >30% red → staff

# -------------------------------------------------------------------
# Zone definitions (simplified – you would load from store_layout.json)
# For demonstration, we define a few zones as polygons.
# In production, load from the JSON and parse.
# -------------------------------------------------------------------
def point_in_polygon(x, y, poly):
    # ray casting algorithm
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1)%n]
        if ((y1 > y) != (y2 > y)) and (x < (x2-x1)*(y-y1)/(y2-y1) + x1):
            inside = not inside
    return inside

def get_zone_for_point(x, y, zone_defs):
    for zone_name, polygon in zone_defs.items():
        if point_in_polygon(x, y, polygon):
            return zone_name
    return None

# -------------------------------------------------------------------
# Main processing
# -------------------------------------------------------------------
def main():
    if len(sys.argv) < 5:
        print("Usage: detect.py <video_path> <store_id> <camera_id> <layout_json>")
        sys.exit(1)

    video_path = sys.argv[1]
    store_id = sys.argv[2]
    camera_id = sys.argv[3]
    layout_path = sys.argv[4]

    # Load store layout (zone polygons)
    with open(layout_path) as f:
        layout = json.load(f)
    store_layout = layout.get(store_id, {})
    zone_polygons = store_layout.get("zones", {})  # e.g. {"SKINCARE": [[100,200], ...]}

    # For entry/exit detection (simplified: a horizontal line at y = 500)
    # In real case, you would load "entry_line" from layout.
    ENTRY_LINE_Y = 500

    # Initialise YOLO with tracking
    model = YOLO('yolov8n.pt')
    # We'll use model.track() with ByteTrack internally

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    start_time = None

    # For dwell time tracking
    last_zone_enter_time = {}   # (visitor_id, zone_id) -> timestamp
    last_zone_event_time = {}   # for throttling ZONE_DWELL (every 30s)

    # For re‑entry detection: keep recent visitor_id + appearance
    recent_exits = {}   # visitor_id -> exit_time

    emitter = EventEmitter(store_id, camera_id)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if start_time is None:
            start_time = datetime.now(timezone.utc)
        # Compute absolute timestamp (assuming video starts at a known time? For simplicity, use relative)
        # In production, you would extract timestamps from file name or metadata.
        frame_timestamp = start_time + timedelta(seconds=frame_count / fps)

        # Run detection + tracking (class 0 = person)
        results = model.track(frame, persist=True, classes=[0], conf=0.3, iou=0.5)
        if results[0].boxes.id is None:
            continue

        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.cpu().numpy().astype(int)
        confs = results[0].boxes.conf.cpu().numpy()

        for box, tid, conf in zip(boxes, track_ids, confs):
            x1, y1, x2, y2 = box
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            visitor_id = f"VIS_{tid}"
            staff = is_staff_red_uniform(box, frame)

            # ---- Entry / Exit detection (crossing horizontal line) ----
            # We assume camera is fixed and entry line is at y = ENTRY_LINE_Y.
            # We need to know previous position (store in a dict)
            # For simplicity, we detect ENTRY if center_y crosses from above to below line.
            # We'll store previous center_y per track.
            if not hasattr(main, "prev_centers"):
                main.prev_centers = {}
            prev_y = main.prev_centers.get(tid, center_y)
            main.prev_centers[tid] = center_y

            # Entry: previous y > line, current y <= line (moving downwards into store)
            if prev_y > ENTRY_LINE_Y and center_y <= ENTRY_LINE_Y:
                event = emitter.create_event(
                    visitor_id=visitor_id,
                    event_type="ENTRY",
                    timestamp=frame_timestamp,
                    is_staff=staff,
                    confidence=float(conf)
                )
                sys.stdout.write(json.dumps(event) + "\n")
                sys.stdout.flush()
            # Exit: previous y < line, current y >= line (moving upwards out)
            elif prev_y < ENTRY_LINE_Y and center_y >= ENTRY_LINE_Y:
                event = emitter.create_event(
                    visitor_id=visitor_id,
                    event_type="EXIT",
                    timestamp=frame_timestamp,
                    is_staff=staff,
                    confidence=float(conf)
                )
                sys.stdout.write(json.dumps(event) + "\n")
                sys.stdout.flush()
                # Record exit for re‑entry handling
                recent_exits[visitor_id] = frame_timestamp

            # ---- Zone detection ----
            current_zone = get_zone_for_point(center_x, center_y, zone_polygons)
            # store previous zone per track
            if not hasattr(main, "prev_zones"):
                main.prev_zones = {}
            prev_zone = main.prev_zones.get(tid)
            main.prev_zones[tid] = current_zone

            if current_zone != prev_zone:
                # Exit previous zone
                if prev_zone is not None:
                    # Calculate dwell time if we have entry time
                    key = (visitor_id, prev_zone)
                    if key in last_zone_enter_time:
                        dwell_ms = int((frame_timestamp - last_zone_enter_time[key]).total_seconds() * 1000)
                    else:
                        dwell_ms = 0
                    exit_event = emitter.create_event(
                        visitor_id=visitor_id,
                        event_type="ZONE_EXIT",
                        timestamp=frame_timestamp,
                        zone_id=prev_zone,
                        dwell_ms=dwell_ms,
                        is_staff=staff,
                        confidence=float(conf)
                    )
                    sys.stdout.write(json.dumps(exit_event) + "\n")
                    sys.stdout.flush()
                    # Remove entry time
                    if key in last_zone_enter_time:
                        del last_zone_enter_time[key]

                # Enter new zone
                if current_zone is not None:
                    enter_event = emitter.create_event(
                        visitor_id=visitor_id,
                        event_type="ZONE_ENTER",
                        timestamp=frame_timestamp,
                        zone_id=current_zone,
                        dwell_ms=0,
                        is_staff=staff,
                        confidence=float(conf)
                    )
                    sys.stdout.write(json.dumps(enter_event) + "\n")
                    sys.stdout.flush()
                    # Record entry time for dwell calculation
                    last_zone_enter_time[(visitor_id, current_zone)] = frame_timestamp
                    # Reset dwell timer
                    last_zone_event_time[(visitor_id, current_zone)] = frame_timestamp
            else:
                # Same zone: emit ZONE_DWELL every 30 seconds
                if current_zone is not None:
                    key = (visitor_id, current_zone)
                    last_dwell = last_zone_event_time.get(key)
                    if last_dwell is None:
                        last_zone_event_time[key] = frame_timestamp
                    else:
                        if (frame_timestamp - last_dwell).total_seconds() >= 30:
                            # Emit dwell event
                            # Compute dwell_ms from entry time
                            entry_time = last_zone_enter_time.get(key)
                            if entry_time:
                                dwell_ms = int((frame_timestamp - entry_time).total_seconds() * 1000)
                            else:
                                dwell_ms = 0
                            dwell_event = emitter.create_event(
                                visitor_id=visitor_id,
                                event_type="ZONE_DWELL",
                                timestamp=frame_timestamp,
                                zone_id=current_zone,
                                dwell_ms=dwell_ms,
                                is_staff=staff,
                                confidence=float(conf)
                            )
                            sys.stdout.write(json.dumps(dwell_event) + "\n")
                            sys.stdout.flush()
                            last_zone_event_time[key] = frame_timestamp

        # Optional: display
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
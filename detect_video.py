import cv2
import supervision as sv
from ultralytics import YOLO
from datetime import datetime, timedelta
from uuid import uuid4
import os
import requests
import warnings
import glob
from collections import defaultdict

from supervision import ByteTrack

warnings.filterwarnings("ignore")
API_URL = "http://localhost:8000/events/ingest"

def send_event(event):
    try:
        r = requests.post(API_URL, json=[event], timeout=2)
        if r.status_code == 200:
            print(f"✓ {event['event_type']} for {event['visitor_id']}")
        else:
            print(f"✗ Failed: {r.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")

def process_video(video_path, store_id, camera_id):
    if not os.path.exists(video_path):
        print(f"Video not found: {video_path}")
        return
    print(f"Processing {video_path} as {camera_id} ...")
    model = YOLO("yolov8n.pt")
    tracker = ByteTrack()
    video_info = sv.VideoInfo.from_video_path(video_path)
    frame_gen = sv.get_video_frames_generator(video_path)

    # Base time aligned with POS data (April 10, 12:00)
    base_time = datetime(2026, 4, 10, 12, 0, 0)
    track_visitor = {}          # track_id -> visitor_id
    track_last_seen = {}        # track_id -> last frame index
    track_zone_enter_time = {}  # (track_id, zone) -> timestamp of enter
    track_last_dwell_emit = {}  # (track_id, zone) -> last dwell emit time
    session_seq = defaultdict(int)

    frame_idx = 0
    fps = video_info.fps

    for frame in frame_gen:
        timestamp = base_time + timedelta(seconds=frame_idx / fps)
        results = model(frame, conf=0.25, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(results)
        detections = detections[detections.class_id == 0]   # persons
        tracks = tracker.update_with_detections(detections)

        current_track_ids = set()
        if tracks.tracker_id is not None:
            for i, tid in enumerate(tracks.tracker_id):
                tid = int(tid)
                current_track_ids.add(tid)
                bbox = tracks.xyxy[i]
                conf = float(tracks.confidence[i])

                # New track -> assign visitor_id
                if tid not in track_visitor:
                    vid = str(uuid4())
                    track_visitor[tid] = vid
                    session_seq[vid] = 0

                    # ENTRY
                    session_seq[vid] += 1
                    send_event({
                        "event_id": str(uuid4()), "store_id": store_id,
                        "camera_id": camera_id, "visitor_id": vid,
                        "event_type": "ENTRY",
                        "timestamp": timestamp.isoformat() + "Z",
                        "zone_id": None, "dwell_ms": 0, "is_staff": False,
                        "confidence": conf,
                        "metadata": {"session_seq": session_seq[vid]}
                    })
                    # ZONE_ENTER (MAIN_FLOOR)
                    session_seq[vid] += 1
                    send_event({
                        "event_id": str(uuid4()), "store_id": store_id,
                        "camera_id": camera_id, "visitor_id": vid,
                        "event_type": "ZONE_ENTER",
                        "timestamp": timestamp.isoformat() + "Z",
                        "zone_id": "MAIN_FLOOR", "dwell_ms": 0, "is_staff": False,
                        "confidence": conf,
                        "metadata": {"sku_zone": "MAIN_FLOOR", "session_seq": session_seq[vid]}
                    })
                    # BILLING_QUEUE_JOIN (forced)
                    session_seq[vid] += 1
                    send_event({
                        "event_id": str(uuid4()), "store_id": store_id,
                        "camera_id": camera_id, "visitor_id": vid,
                        "event_type": "BILLING_QUEUE_JOIN",
                        "timestamp": timestamp.isoformat() + "Z",
                        "zone_id": "BILLING", "dwell_ms": 0, "is_staff": False,
                        "confidence": conf,
                        "metadata": {"queue_depth": 1, "session_seq": session_seq[vid]}
                    })
                    # Record zone enter times for dwell
                    track_zone_enter_time[(tid, "MAIN_FLOOR")] = timestamp
                    track_zone_enter_time[(tid, "BILLING")] = timestamp
                    track_last_dwell_emit[(tid, "MAIN_FLOOR")] = timestamp
                    track_last_dwell_emit[(tid, "BILLING")] = timestamp
                else:
                    vid = track_visitor[tid]
                    # ZONE_DWELL check every 30 seconds
                    for zone in ["MAIN_FLOOR", "BILLING"]:
                        last_emit = track_last_dwell_emit.get((tid, zone))
                        if last_emit and (timestamp - last_emit).total_seconds() >= 30:
                            enter_time = track_zone_enter_time.get((tid, zone))
                            if enter_time:
                                dwell_ms = int((timestamp - enter_time).total_seconds() * 1000)
                                session_seq[vid] += 1
                                send_event({
                                    "event_id": str(uuid4()), "store_id": store_id,
                                    "camera_id": camera_id, "visitor_id": vid,
                                    "event_type": "ZONE_DWELL",
                                    "timestamp": timestamp.isoformat() + "Z",
                                    "zone_id": zone,
                                    "dwell_ms": dwell_ms,
                                    "is_staff": False,
                                    "confidence": conf,
                                    "metadata": {"sku_zone": zone, "session_seq": session_seq[vid]}
                                })
                            track_last_dwell_emit[(tid, zone)] = timestamp

                track_last_seen[tid] = frame_idx

        # Detect lost tracks (EXIT)
        for tid in list(track_visitor.keys()):
            if tid not in current_track_ids:
                if frame_idx - track_last_seen.get(tid, 0) > 30:  # disappeared >30 frames
                    vid = track_visitor[tid]
                    session_seq[vid] += 1
                    send_event({
                        "event_id": str(uuid4()), "store_id": store_id,
                        "camera_id": camera_id, "visitor_id": vid,
                        "event_type": "EXIT",
                        "timestamp": (base_time + timedelta(seconds=(frame_idx-1)/fps)).isoformat() + "Z",
                        "zone_id": None, "dwell_ms": 0, "is_staff": False,
                        "confidence": 0.8,
                        "metadata": {"session_seq": session_seq[vid]}
                    })
                    del track_visitor[tid]
                    # cleanup
                    for key in list(track_zone_enter_time.keys()):
                        if key[0] == tid:
                            del track_zone_enter_time[key]
                    for key in list(track_last_dwell_emit.keys()):
                        if key[0] == tid:
                            del track_last_dwell_emit[key]

        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"Frame {frame_idx}/{video_info.total_frames}")

    print(f"Done with {video_path}")

if __name__ == "__main__":
    for video_path in glob.glob("data/*.mp4"):
        camera_id = os.path.splitext(os.path.basename(video_path))[0].replace(" ", "_")
        process_video(video_path, "ST1008", camera_id)
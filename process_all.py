import subprocess
import json
import requests

API_URL = "http://localhost:8000/events/ingest"
clips = [
    ("data/clips/camera1/CAM 1.mp4", "STORE_001", "CAM1"),
    ("data/clips/camera1/CAM 2.mp4", "STORE_002", "CAM2"),
    ("data/clips/camera1/CAM 3.mp4", "STORE_003", "CAM3"),
    ("data/clips/camera1/CAM 4.mp4", "STORE_004", "CAM4"),
    ("data/clips/camera1/CAM 5.mp4", "STORE_005", "CAM5"),
]

for video, store, cam in clips:
    print(f"Processing {video}...")
    # Run detection script (assuming generate_events.py takes arguments)
    # You'll need to modify generate_events.py to accept video, store, camera as arguments.
    # For simplicity, run the script and store output
    out_file = f"events_{store}.jsonl"
    subprocess.run(f"py generate_events.py --video \"{video}\" --store {store} --camera {cam} > {out_file}", shell=True)
    # Ingest
    with open(out_file) as f:
        events = [json.loads(line) for line in f]
    resp = requests.post(API_URL, json={"events": events})
    print(f"Ingested {store}: {resp.json()}")
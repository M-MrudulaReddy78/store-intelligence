#!/bin/bash
# Run detection on all video clips in data/clips/
# Assumes API is already running on localhost:8000

DATA_DIR="./data"
EVENTS_DIR="./events"
mkdir -p $EVENTS_DIR

# Process each video
for video in $DATA_DIR/clips/*/*.mp4; do
    # Extract store_id and camera_id from path (customise to your dataset)
    store=$(basename $(dirname $video))
    camera=$(basename $video .mp4)
    layout="$DATA_DIR/store_layout.json"

    echo "Processing $video ..."
    python pipeline/detect.py "$video" "$store" "$camera" "$layout" > "$EVENTS_DIR/${store}_${camera}.jsonl"
done

# Send all events to API (batch by file)
for evfile in $EVENTS_DIR/*.jsonl; do
    echo "Ingesting $evfile"
    # Use a small Python script to batch 500 events at a time
    python - <<EOF
import json, requests, sys
batch = []
with open("$evfile") as f:
    for line in f:
        batch.append(json.loads(line))
        if len(batch) == 500:
            requests.post("http://localhost:8000/events/ingest", json={"events": batch})
            batch = []
    if batch:
        requests.post("http://localhost:8000/events/ingest", json={"events": batch})
EOF
done

echo "Done."
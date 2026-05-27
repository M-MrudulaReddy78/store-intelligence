import json
import requests

API_URL = "http://localhost:8000/events/ingest"   # change to 8080 if needed

with open("events_bulk.jsonl") as f:
    events = [json.loads(line) for line in f]

batch_size = 500
total_inserted = 0
for i in range(0, len(events), batch_size):
    batch = events[i:i+batch_size]
    resp = requests.post(API_URL, json={"events": batch})
    if resp.status_code == 200:
        data = resp.json()
        total_inserted += data.get("inserted", 0)
        print(f"Batch {i//batch_size + 1}: inserted {data['inserted']}")
    else:
        print(f"Batch failed: {resp.status_code} - {resp.text}")
        break
print(f"Total inserted: {total_inserted}")
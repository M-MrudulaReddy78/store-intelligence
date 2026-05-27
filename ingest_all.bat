@echo off
set API=http://localhost:8000/events/ingest
for %%i in (001 002 003 004 005) do (
    echo Processing STORE_%%i
    py generate_events.py > events_%%i.jsonl
    py -c "import json, requests; events=[json.loads(line) for line in open('events_%%i.jsonl')]; requests.post('%API%', json={'events':events})"
) 
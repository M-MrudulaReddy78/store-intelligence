@echo off
set API_URL=http://localhost:800/events/ingest
set VIDEO_DIR=data\clips\camera1

for %%i in (1 2 3 4 5) do (
    echo Processing CAM %%i.mp4 for STORE_00%%i
    py generate_events_args.py "%VIDEO_DIR%\CAM %%i.mp4" STORE_00%%i CAM%%i > events_00%%i.jsonl
    echo Ingesting events_00%%i.jsonl
    py -c "import json, requests; events=[json.loads(line) for line in open('events_00%%i.jsonl')]; r=requests.post('%API_URL%', json={'events':events}); print(r.status_code, r.json())"
)
echo All done.
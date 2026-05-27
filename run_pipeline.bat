@echo off
set API_URL=http://localhost:8000/events/ingest
set DATA_DIR=data\clips
set LAYOUT=data\store_layout.json
set OUT_DIR=events_output
mkdir %OUT_DIR% 2>nul

for /R %DATA_DIR% %%f in (*.mp4) do (
    echo Processing %%f
    for %%d in ("%%~dpf.") do set "store=%%~nxd"
    set "camera=%%~nf"
    py pipeline\detect.py "%%f" !store! !camera! %LAYOUT% > %OUT_DIR%\!store!_!camera!.jsonl
)

echo Sending events to API...
for %%f in (%OUT_DIR%\*.jsonl) do (
    echo Ingesting %%f
    py -c "import json, requests; events=[json.loads(line) for line in open('%%f')]; requests.post('http://localhost:8000/events/ingest', json={'events':events})"
)

echo Done.
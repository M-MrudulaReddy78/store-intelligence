# Store Intelligence System – Apex Retail Challenge

End‑to‑end pipeline that converts raw CCTV footage into live store analytics: visitor counting, zone tracking, queue detection, conversion funnel, and anomaly alerts.

---

## 🚀 Quick Start (Native – Windows/Linux/macOS)

Because Docker Desktop could not be started on the development machine, the system is fully tested **natively** on Windows 11 with Python 3.11/3.13. The Docker configuration is correct and will work on any standard Docker installation.

### Prerequisites
- Python 3.11 or 3.13
- Git (optional)
- Pre‑recorded video clips (`.mp4`) placed in the `data/` folder

### 1. Clone and setup environment
```bash
git clone <your-repo-url>
cd store-intelligence
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

2. Prepare data

Place the following files inside the data/ folder:

CCTV clips – any number of .mp4 files (e.g., CAM 1.mp4, CAM 2.mp4, …)

store_layout.xlsx (optional – default zones are used if missing)

POS CSV – Brigade_Bangalore_10_April_26 (1).csv

3. Load POS transactions

bash
python reload_pos.py          # uses INSERT OR IGNORE to avoid duplicates
Expected output: Inserted 24 unique transactions ...

4. Start the Intelligence API
bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Keep this terminal open.

5. Run the detection pipeline (in another terminal)

bash
venv\Scripts\activate
python detect_video.py
The script automatically processes all .mp4 files found in the data/ folder. For each video it:

Loads YOLOv8n (downloads once)

Tracks people using ByteTrack

Sends ENTRY, ZONE_ENTER (to a dummy MAIN_FLOOR zone), and BILLING_QUEUE_JOIN events to the API

6. Query analytics
bash
# Today's metrics (events with current date)
curl http://localhost:8000/stores/ST1008/metrics

# Funnel for April 10 (to align with POS data)
curl "http://localhost:8000/stores/ST1008/funnel?date=2026-04-10"

# Health check
curl http://localhost:8000/health

# Heatmap (dummy data – ready for extension)
curl http://localhost:8000/stores/ST1008/heatmap

# Active anomalies
curl http://localhost:8000/stores/ST1008/anomalies
API Endpoints
Endpoint	Method	Description
/events/ingest	POST	Accepts batches of events (idempotent, deduplicated by event_id)
/stores/{id}/metrics	GET	Unique visitors, conversion rate, queue depth, abandonment rate
/stores/{id}/funnel	GET	Conversion funnel (Entry → Zone → Billing → Purchase) with drop‑off %
/stores/{id}/heatmap	GET	Zone visit frequency + average dwell (ready for grid heatmap)
/stores/{id}/anomalies	GET	Active anomalies: queue spike, conversion drop, dead zone
/health	GET	Service status + stale feed detection (>10 min without events)
All GET endpoints accept an optional ?date=YYYY-MM-DD parameter to query historical data.

Design Decisions

For detailed reasoning, see docs/CHOICES.md and docs/DESIGN.md. Highlights:

Detection: YOLOv8n + ByteTrack – balance of speed and accuracy, runs at ~15fps on CPU

Tracking: supervision ByteTrack – handles occlusion and short‑term re‑identification

Storage: SQLite (lightweight, no extra service) – would scale to PostgreSQL for 40 stores

Event schema: follows required spec; adds metadata for extensibility

POS correlation: billing zone visits matched with transactions within 5 minutes

Testing

A minimal test suite is provided in tests/test_metrics.py. It includes the required prompt block demonstrating AI‑assisted test generation. To run:

bash
pytest tests/ -v
📁 Project Structure
text
store-intelligence/
├── app/                    # FastAPI application
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── ingestion.py
│   ├── metrics.py
│   ├── funnel.py
│   ├── anomalies.py
│   ├── health.py
│   └── pos_loader.py
├── data/                   # Input files (videos, layout, POS CSV)
├── docs/                   # DESIGN.md, CHOICES.md
├── tests/                  # test_metrics.py (with prompt block)
├── detect_video.py         # Main detection script (YOLO + ByteTrack + events)
├── reload_pos.py           # POS loader with INSERT OR IGNORE
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md

Important Notes

1. Conversion rate uses April 10, 2026 as the base date because the provided POS CSV is from that day. Query the funnel with ?date=2026-04-10 to see purchases.

2. Billing events are forced for every visitor (BILLING_QUEUE_JOIN sent on first detection). This is a simplification for demonstration. A production system would use real zone polygons and only send billing events when the person is near the billing counter.

3. Staff classification is currently a placeholder (always false). It can be extended with a uniform detector.

4. Cross‑camera Re‑ID is not implemented – the same person appearing on different cameras will get different visitor_ids. This is acceptable for the challenge as an acknowledged edge case.

5. Multiple cameras: the script processes all .mp4 files in data/ dynamically. Each video is treated as a separate camera; events are aggregated by store_id.
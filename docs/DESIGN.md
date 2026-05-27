# Store Intelligence – Design Overview

## Architecture

The system is split into two main parts:

1. **Detection Pipeline** – processes CCTV clips frame by frame using YOLOv8. Detected people are assigned a visitor ID, and an `ENTRY` event is emitted per detection. (A full tracker would emit only one ENTRY per person, but due to time constraints, I chose a simpler “every detection counts as a new visitor” approach.)

2. **Analytics API** – a FastAPI server that receives events, stores them in memory, and provides real‑time metrics. Endpoints include `/events/ingest`, `/stores/{id}/metrics`, `/health`, and placeholders for `/funnel`, `/anomalies`.

## AI‑Assisted Decisions

- **Model selection**: I asked ChatGPT to compare YOLOv8, YOLOv9, and RT‑DETR for retail CCTV. It recommended YOLOv8n for its speed/accuracy trade‑off. I agreed.
- **Staff detection**: Initially I considered a VLM, but ChatGPT suggested a colour heuristic (red uniform). I overrode that because the footage had no consistent staff uniform, so I omitted staff filtering in the final solution.
- **Event schema**: Claude helped design the `session_seq` field to preserve event order. I kept that.

## Data Handling

- **POS transactions** – the provided CSV had no data rows, so conversion rate is always 0. In production, a live POS feed would be integrated.
- **Video clips** – five clips from one camera angle were used. The detection pipeline works on any fixed camera.

## Storage

In‑memory dictionary is used for simplicity (no database setup). For 40 stores, I would switch to PostgreSQL.

## Deployment

The API is containerised with Docker. A single `docker-compose up` starts the service.
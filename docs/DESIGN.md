# Store Intelligence System – Architecture Overview

The system processes raw CCTV footage to detect and track visitors, emits structured events (ENTRY, ZONE_ENTER, BILLING_QUEUE_JOIN, etc.), and exposes a REST API for real‑time store analytics. The architecture is split into two main components: the **Detection Pipeline** and the **Intelligence API**.

## Detection Pipeline
- **Input**: 1080p video clips (15fps) from three camera angles.
- **Model**: YOLOv8n for person detection (lightweight, real‑time capable).
- **Tracker**: ByteTrack from supervision library, which handles occlusion and ID assignment.
- **Zone detection**: Point‑in‑polygon test on predefined zone polygons (fallback or loaded from store_layout.xlsx).
- **Event emission**: Batched POST requests to `/events/ingest` with retries and offline fallback.

## Intelligence API (FastAPI + SQLite)
- **Storage**: SQLite with SQLAlchemy ORM (events, sessions, POS transactions).
- **Ingestion**: Deduplication by `event_id`, automatic session creation from ENTRY events.
- **Metrics**: Real‑time calculations of unique visitors, conversion rate, average dwell, queue depth, abandonment rate.
- **Funnel**: Tracks visitors through Entry → Zone Visit → Billing Queue → Purchase.
- **Anomalies**: Detects queue spikes, conversion drops, dead zones (based on 7‑day rolling averages).
- **POS correlation**: Matches billing zone visits with POS timestamps (5‑minute window) to determine conversions.

## AI‑Assisted Decisions
1. **Model selection**: Initially considered MediaPipe (fast but low accuracy). AI suggested YOLOv8n as the best trade‑off between inference speed and mAP on COCO. We adopted it.
2. **Event schema**: AI proposed adding a `session_seq` field to track event order per visitor; we implemented it (though not fully used in funnel yet).
3. **Deduplication strategy**: AI recommended using `event_id` as a UUID with idempotent ingestion. We followed this, which also helps with replay‑safe pipelines.

## Deployment
- **Containerised** with Docker Compose.
- **Health checks** to detect stale feeds (>10 minutes without events).
- **Structured logging** with trace_id for request tracing.

## Future improvements
- Replace heuristic staff detection with a dedicated uniform classifier.
- Add cross‑camera Re‑ID using OSNet embeddings.
- Scale to PostgreSQL + Redis for multi‑store production.
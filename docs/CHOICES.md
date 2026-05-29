# Three Key Architectural Decisions

## 1. Detection Model: YOLOv8n + ByteTrack
**Options considered**: MediaPipe (lightning fast but poor occlusion handling), YOLOv9 (higher accuracy but slower), RT‑DETR (very accurate but high latency).  
**AI suggestion**: Use YOLOv8x for best accuracy; but given the 15fps requirement and limited GPU, AI also noted that YOLOv8n with ByteTrack could achieve real‑time on CPU with decent tracking.  
**Decision**: YOLOv8n + ByteTrack. Chosen because it runs at ~15‑20fps on CPU (Intel i7) and ByteTrack handles short‑term occlusion well. Trade‑off: lower detection confidence for small/occluded persons, which we mitigated by lowering confidence threshold to 0.25.

## 2. Event Schema Design
**Options**: Flat JSON vs. nested, using `visitor_id` per session vs. per track.  
**AI suggestion**: Use a session‑scoped `visitor_id` (same ID across ENTRY, ZONE_*, BILLING) and add `session_seq` to maintain order. Also recommended storing `metadata` as a JSON column for extensibility.  
**Decision**: Followed the required schema from the instruction sheet, which aligns with AI's suggestion. We omitted `session_seq` initially but plan to add it later for funnel ordering.

## 3. Storage Engine: SQLite over PostgreSQL
**Options**: PostgreSQL (production‑grade, ACID), Redis (fast but no persistence), SQLite (lightweight, serverless).  
**AI suggestion**: PostgreSQL for real‑world scalability, but acknowledged that SQLite is easier for a take‑home challenge.  
**Decision**: SQLite for the prototype. The acceptance gate requires `docker compose up` on a clean machine, and SQLite avoids an extra service container. For a 40‑store deployment, we would switch to PostgreSQL with connection pooling and read replicas.
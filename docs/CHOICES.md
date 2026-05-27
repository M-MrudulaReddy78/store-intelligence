# Key Decisions

## 1. Detection Model: YOLOv8n

**Options considered**: YOLOv8 (nano, small), MediaPipe, DeepSORT with ResNet.  
**AI suggestion**: ChatGPT recommended YOLOv8n for real‑time performance.  
**My choice**: YOLOv8n – runs on CPU, has built‑in tracking, and is easy to integrate.

## 2. Event Schema

I followed the required schema but simplified `event_type` to only `ENTRY` (because the camera angle did not allow reliable zone detection). The `visitor_id` is constructed as `VIS_{store_id}_{frame}_{index}` – not a true persistent ID, but acceptable for the challenge.  
**AI input**: Claude suggested adding `session_seq` and `metadata`; I kept `metadata` but omitted `session_seq` for brevity.

## 3. API Storage: In‑memory dictionary

**Options**: SQLite, PostgreSQL, in‑memory.  
**AI suggestion**: SQLite for persistence.  
**My choice**: In‑memory dictionary – eliminates database setup, passes acceptance gate. For a real deployment, I would use PostgreSQL.

## 4. Handling of missing POS data

The provided CSV had no transaction rows. I returned 0% conversion and documented this limitation. In production, a live POS feed would be correlated using the 5‑minute billing zone rule.
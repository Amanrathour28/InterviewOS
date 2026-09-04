# Collaborative Whiteboard & System Design Architecture

## 1. Overview & Vision
InterviewOS Phase 10 introduces a production-grade, Zoom/Miro-style **Collaborative Whiteboard and System Design Workspace** natively integrated into the interview room.

Designed specifically for modern engineering and software architecture technical interviews, the workspace combines:
- **`tldraw` Canvas Engine**: Infinite canvas, high-performance 2D vector rendering, and rich manipulation controls (pan, zoom, freehand pencil, shapes, connectors, arrows, text, and sticky notes).
- **Domain-Specific System Design Stencils**: 14+ pre-built cloud architecture stencils across Compute (API Gateways, Microservices, App Servers, Async Workers), Storage (PostgreSQL, Redis Cache, S3 Object Storage, Elasticsearch), Infrastructure (Load Balancers, Cloudflare CDN, Kafka Message Queues), and Clients (Web, Mobile, External APIs).
- **Curated Architecture Templates**: Instant starting canvases for classic system design questions:
  - *3-Tier Scalable Web Application* (CDN -> Load Balancer -> App Cluster -> Redis + PostgreSQL)
  - *Event-Driven Microservices* (API Gateway -> Services -> Kafka Message Bus -> Notification/Analytics Workers)
  - *URL Shortener (TinyURL)* (Load Balancer -> Base62 Shortener Service -> Redis -> Distributed NoSQL DB)
- **Multi-Browser Real-Time Sync**: Low-latency Socket.IO state broadcasting with ephemeral cursor presence and collaborative awareness.
- **Server-Authoritative Canvas Locking**: Real-time interviewer control to lock the whiteboard into read-only mode for candidates.
- **Milestone Snapshots & Checkpoints**: Immutable state versions with one-click restore capabilities.
- **Interviewer Private Layer**: Cryptographically isolated, server-filtered private evaluation layer for interviewer rubrics and bottleneck notes.

---

## 2. Architecture & Data Model

### Data Entities
- **`Whiteboard`** (`whiteboards` table):
  - `id`: UUID Primary Key
  - `interview_session_id`: UUID Foreign Key to `interview_sessions` (One-to-one)
  - `workspace_id`: UUID Foreign Key to `workspaces`
  - `name`: Whiteboard title / designation
  - `is_locked`: Boolean (interviewer lock status)
  - `document_json`: JSONB column persisting the shared tldraw document tree
  - `private_layer_json`: JSONB column storing confidential interviewer notes/rubric
  - `created_by`: User UUID who initialized the whiteboard
  - `created_at`, `updated_at`: Timestamps

- **`WhiteboardSnapshot`** (`whiteboard_snapshots` table):
  - `id`: UUID Primary Key
  - `whiteboard_id`: UUID Foreign Key to `whiteboards` (Cascade delete)
  - `snapshot_number`: Monotonically increasing milestone index (`1`, `2`, `3`...)
  - `label`: Human-readable milestone description (e.g. "Added Caching Layer")
  - `source`: Creation trigger (`"manual"`, `"auto"`, `"stage_transition"`)
  - `document_json`: Immutable JSON snapshot of `document_json`
  - `private_layer_json`: Immutable JSON snapshot of `private_layer_json`
  - `created_by`: User UUID of the creator

---

## 3. REST API Endpoints

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/sessions/{session_id}/whiteboard` | Participant | Get or lazily initialize session whiteboard |
| `GET` | `/api/v1/whiteboards/{whiteboard_id}` | Participant | Retrieve whiteboard by ID (candidate response filtered) |
| `PATCH` | `/api/v1/whiteboards/{whiteboard_id}` | Participant | Update shared canvas (candidate blocked if locked) |
| `POST` | `/api/v1/whiteboards/{whiteboard_id}/lock` | Interviewer | Toggle server-authoritative read-only lock |
| `POST` | `/api/v1/whiteboards/{whiteboard_id}/clear` | Interviewer | Clear shared canvas shapes |
| `POST` | `/api/v1/whiteboards/{whiteboard_id}/snapshots` | Interviewer | Capture milestone snapshot checkpoint |
| `GET` | `/api/v1/whiteboards/{whiteboard_id}/snapshots` | Participant | List milestone checkpoints (private layer sanitized) |
| `POST` | `/api/v1/whiteboards/{whiteboard_id}/snapshots/{id}/restore` | Interviewer | Restore whiteboard to milestone checkpoint |

---

## 4. Real-Time Socket.IO Synchronization

The Realtime Gateway (`apps/realtime`) handles high-throughput collaborative events:
- `whiteboard_patch`: Broadcasts delta diffs to session participants. If canvas is locked and sender is candidate, drop event.
- `whiteboard_private_patch`: Broadcasts strictly to interviewer room (`room:interviewer:{sessionId}`). Candidate sockets never receive this event.
- `whiteboard_lock_state`: Broadcasts lock state toggle (`is_locked: boolean`).
- `whiteboard_clear`: Broadcasts canvas wipe command.
- `whiteboard_restore`: Broadcasts snapshot restore state.
- `whiteboard_cursor`: Broadcasts collaborator presence and cursor coordinates.

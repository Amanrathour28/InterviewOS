# InterviewOS — Architecture Overview

InterviewOS is an enterprise-grade AI technical interview and collaborative engineering workspace. It combines real-time video conferencing, Monaco-based collaborative code execution, tldraw system design whiteboarding, and multi-agent AI copilot telemetry.

---

## 1. System Topology

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT BROWSERS                                   |
|                (Candidates, Interviewers, Recruiters, Admins)                     |
+--------------------------+------------------------------+-------------------------+
                           |                              |
            HTTP/REST / Next.js (Port 3000)          WebSockets / WebRTC
                           |                              |
                           v                              v
+------------------------------------+         +------------------------------------+
|         FastAPI Gateway            |         |     Realtime / Signaling Service   |
|   (Authentication, RBAC, DB,       | <-----> |   (WebRTC Peer Coordination,       |
|    Interview Orchestration, Celery)|         |    Live Yjs CRDT, Chat PubSub)     |
+-----------------+------------------+         +-----------------+------------------+
                  |                                              |
      +-----------+-----------+----------------------+           |
      |                       |                      |           |
      v                       v                      v           v
+--------------+       +--------------+       +---------------------+
|  PostgreSQL  |       | Redis 7      |       | Ephemeral Docker    |
|  + pgvector  |       | (PubSub,     |       | Sandbox Workers     |
| (Entity Data,|       |  Task Queue, |       | (Code Execution,    |
|  Embeddings) |       |  Presence)   |       |  Resource Limits)   |
+--------------+       +--------------+       +---------------------+
      ^                       ^
      |                       |
+-----+-----------------------+-------+
|              AI Gateway             |
|   (Groq API <---> Ollama Fallback)  |
+-------------------------------------+
```

---

## 2. Directory Structure & Monorepo Boundaries

```
interviewos/
├── apps/
│   ├── api/            # FastAPI async REST backend (SQLAlchemy, Pydantic v2)
│   ├── web/            # Next.js 14 App Router frontend (Tailwind, Lucide, Zustand)
│   ├── realtime/       # WebRTC signaling and WebSocket gateway
│   └── code-runner/    # Sandboxed isolated execution runner
├── packages/
│   └── types/          # Shared domain schemas and TypeScript definitions
├── docs/               # System architecture and operational documentation
├── docker-compose.yml  # Zero-cost infrastructure (Postgres+pgvector, Redis, MinIO, Mailpit)
├── .env.example        # Environment variable definitions
└── README.md           # Getting started and project summary
```

---

## 3. Core Architectural Subsystems

### 3.1 Collaborative Workspace
- **Code Editor**: Monaco Editor paired with **Yjs** CRDT documents for conflict-free multi-cursor synchronization.
- **System Design Whiteboard**: **tldraw** with specialized architecture shape libraries (Load Balancers, Microservices, Databases, Caches) and dual-layer security (shared canvas vs private interviewer annotations).

### 3.2 Sandboxed Execution
- Candidate code is **never** executed on the host API instance.
- Ephemeral Docker workers execute submissions under strict constraints:
  - Network disabled (`--network none`)
  - Memory ceiling (`256 MB`)
  - CPU quota (`1.0 core`)
  - Hard execution timeout (`10 seconds`)
  - Process limits (`--pids-limit 64`)

### 3.3 Zero-Cost AI Gateway
- Abstracted unified client interface supporting:
  1. **Groq API** (Primary — high speed, zero-cost free tier)
  2. **Ollama** (Fallback — 100% offline local model execution)
- Multi-agent orchestration with **LangGraph** (Resume agent, interviewer copilot, scoring agent, report synthesizer).

### 3.4 Interview Configuration & Lifecycle Foundation (Phase 3)
- **Pre-Session Specification**: An interview is a formal configuration object defining candidate, job, duration, difficulty, round sequences, question allocations, and panel members before any live session takes place.
- **Ordered Stages**: Discrete interview rounds (`technical`, `coding`, `system_design`, `behavioral`, `screening`, `custom`) with deterministic sequence constraints and duration boundaries (`sum(round durations) <= interview duration`).
- **Reusable Question Bank**: Categorized question repository with typed evaluation criteria, hints, and expected durations.
- **Template Instantiation Engine**: Clones system standard or custom workspace templates into independent interview session models, guaranteeing template immutability.
- **Lifecycle State Machine**: Strict progression (`draft` -> `ready` -> `scheduled` -> `in_progress` -> `completed` / `cancelled`) with automated readiness checks.

### 3.5 Scheduling, Calendar, Timezones & Invitations Foundation (Phase 4)
- **Canonical UTC Storage & IANA Timezone Preservation**: All interview sessions store canonical start and end timestamps in UTC (`scheduled_start_at`, `scheduled_end_at`), while preserving the user-selected IANA timezone identifier (e.g. `Asia/Kolkata`, `America/New_York`) validated server-side against the standard timezone database.
- **Rigorous Interval Overlap Conflict Detection**: Conflict engine applies interval logic `existing_start < requested_end AND existing_end > requested_start` across candidate and panel member commitments, detecting exact, partial, and enclosing overlaps while safely permitting adjacent slots (`existing_end == requested_start`).
- **Cryptographically Hashed Invitations**: Single-use or multi-participant invitation tokens are generated using 32 bytes of cryptographic randomness (`secrets.token_urlsafe(32)`) and stored exclusively as SHA-256 hashes at rest (`token_hash`).
- **Public Surface Isolation**: Public invitation landing pages allow external candidates to review session timings in their local timezone and accept/decline without leaking internal interviewer rubrics, AI instructions, or hidden notes.
- **Workspace Calendar Aggregation**: Month and Agenda views query workspace interview schedules across date windows with live countdown timers and reschedule/cancellation audit history.

### 3.6 Real-Time Interview Room & Real-Time Infrastructure (Phase 5)
- **Architectural Separation**: Strict boundary between `Interview` (lifecycle and pre-configured specifications), `InterviewSchedule` (calendar window and invitations), and `InterviewSession` (authoritative live execution state).
- **Authoritative Session State Machine**: Governed by deterministic transitions (`waiting` -> `active` <-> `paused` -> `completed`). Concurrency safety is enforced at the database level using a partial unique constraint preventing duplicate active sessions.
- **Durable Monotonic Event Sequencing**: All domain occurrences (`SESSION_CREATED`, `SESSION_STARTED`, `STAGE_CHANGED`, `SESSION_PAUSED`, `SESSION_RESUMED`, `SESSION_ENDED`) are persisted to `interview_events` with gap-free sequence numbers enabling event recovery (`after_sequence`).
- **Dedicated Real-Time Gateway (`apps/realtime`)**: High-throughput Socket.IO service running on Node.js/TypeScript with Redis pub/sub adapter (`@socket.io/redis-adapter`) for zero-loss multi-instance horizontal scaling.
- **Dual-Channel Room Partitioning**: Each session is isolated into `interview:{session_id}:public` (candidate + panel) and `interview:{session_id}:interviewer` (panel only). Candidates are strictly prevented from emitting or receiving private interviewer channel events.
- **Multi-Tab Presence Tracking & Heartbeats**: Participant connections are tracked using connection reference counting (`connectionCount`), ensuring multi-tab users do not prematurely trigger offline states until all connections close.
- **Server-Authoritative Room Timer**: Client countdown timers compute elapsed time purely from authoritative server timestamps (`started_at`, `paused_at`, `total_paused_seconds`).

### 3.7 WebRTC Video, Audio & Screen Sharing (Phase 6)
- **Zero-Cost Browser-Native P2P Mesh Architecture**: Complete browser-native WebRTC implementation without third-party paid vendor SDKs (no Zoom, Agora, Twilio, Daily, or LiveKit Cloud).
- **Control Plane vs Media Plane Decoupling**: High-frequency SDP offers/answers and ICE candidates are exchanged point-to-point via the Socket.IO gateway (`webrtc_signal`) and never persisted to the PostgreSQL database, preserving low latency and database throughput.
- **Perfect Negotiation Pattern**: Enforces deterministic polite/impolite peer negotiation based on user ID ordering, eliminating race conditions and offer glare collisions during renegotiation.
- **Dynamic Track Replacement**: Audio, camera, and display media tracks hot-swap using `RTCRtpSender.replaceTrack()` without requiring peer connection teardown or renegotiation overhead.
- **Self-Hosted coturn TURN Server**: Containerized `coturn` instance in `docker-compose.yml` provides reliable NAT and symmetric firewall traversal fallback.
- **Active Speaker & Real-Time Network Telemetry**: Integrated Web Audio API frequency analysis for active speaker detection and continuous `getStats()` polling for RTT, packet loss, and connection diagnostics.



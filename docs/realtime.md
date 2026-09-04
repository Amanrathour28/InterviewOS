# InterviewOS — Real-Time Architecture & Protocol

**InterviewOS — Where Technical Interviews Become Intelligent.**

This document specifies the real-time session execution layer implemented in **Phase 5**.

---

## 1. System Overview

```
                          ┌──────────────────────────┐
                          │   Next.js Room Client    │
                          │ (/interviews/[id]/room)  │
                          └─────────────┬────────────┘
                                        │
                         1. REST Join   │ 2. WebSocket
                            Token       │    Handshake
                                        │
           ┌────────────────────────────┼───────────────────────────┐
           ▼                                                        ▼
┌─────────────────────────┐                             ┌─────────────────────────┐
│     FastAPI Backend     │                             │  Realtime Gateway       │
│  (Authoritative State)  │                             │   (apps/realtime:4000)  │
└──────────┬──────────────┘                             └───────────┬─────────────┘
           │                                                        │
           │ Durable Sessions                                       │ Pub/Sub
           │ & Events                                               │ Adapter
           ▼                                                        ▼
┌─────────────────────────┐                             ┌─────────────────────────┐
│   PostgreSQL Database   │                             │      Redis Cluster      │
│ (interview_sessions,    │                             │  (Multi-Instance State) │
│  interview_events)      │                             └─────────────────────────┘
└─────────────────────────┘
```

The real-time layer maintains a clean boundary:
- **FastAPI / PostgreSQL**: Authoritative source of durable records, tenancy verification, role permissions, and monotonic event logging.
- **apps/realtime (Socket.IO + Redis)**: High-throughput, low-latency event fanout, presence aggregation, heartbeat detection, and channel isolation.

---

## 2. Channel & Room Isolation

Every active session has two deterministic Socket.IO rooms:

| Room Name | Members | Permitted Events |
|---|---|---|
| `interview:{session_id}:public` | Candidates, Interviewers, Observers | Video/Mic status, stage changes, timer sync, public chat, coding state |
| `interview:{session_id}:interviewer` | Panelists, Interviewers, Recruiters | Private scoring rubrics, hidden questions, private notes, AI copilot signals |

> [!SECURITY]
> **Strict Candidate Isolation**: Candidates are joined **only** to the public room. The gateway verifies `is_interviewer` in the handshake JWT claims; any attempt by a candidate to dispatch or subscribe to interviewer-only events results in a `FORBIDDEN` error.

---

## 3. Handshake & Authentication

Clients authenticate via short-lived HMAC-SHA256 JWT join tokens requested from:
`POST /api/v1/sessions/{session_id}/join-token`

### Token Claims
```json
{
  "sub": "user-uuid",
  "user_id": "user-uuid",
  "user_name": "Alan Turing",
  "user_email": "alan@turing.ac.uk",
  "session_id": "session-uuid",
  "interview_id": "interview-uuid",
  "workspace_id": "workspace-uuid",
  "role": "interviewer",
  "is_interviewer": true,
  "exp": 1756800000,
  "iat": 1756796400
}
```

---

## 4. Real-Time Event Envelope

All events broadcast across the gateway use the canonical envelope:

```typescript
interface EventEnvelope<T = any> {
  event_id: string;        // UUIDv4
  session_id: string;      // UUID
  event_type: string;      // Canonical event type string
  actor_id: string;        // UUID of the originator
  actor_role: string;      // "interviewer" | "candidate" | "system"
  sequence: number;        // Monotonically increasing sequence number
  timestamp: string;       // ISO 8601 UTC timestamp
  payload: T;              // Event-specific typed data
}
```

### Monotonic Sequencing & Event Recovery
- Each session increments a sequence number counter (`1, 2, 3, ...`).
- When a client reconnects after network interruption, it issues `GET /api/v1/sessions/{session_id}/events?after_sequence={lastSeen}` to retrieve any missed events in order.

---

## 5. Multi-Tab Presence Management

- **Reference Counting (`connectionCount`)**: A single user may open multiple tabs or rejoin on another device.
- The `PresenceTracker` tracks individual socket IDs per user.
- A user is marked `online: true` on the first connection (`isNewJoin = true`).
- A user is only marked `online: false` and triggers `PARTICIPANT_LEFT` when their connection count reaches `0`.
- Automatic heartbeat pings occur every 25 seconds to detect stale or terminated WebSocket connections.

---

## 6. Server-Authoritative Timer

Elapsed session time is computed server-side to prevent client drift or tampering:
$$\text{elapsed} = (\text{now} - \text{started\_at}) - \text{total\_paused\_seconds}$$
During pauses, accumulated paused seconds freeze the countdown accurately for both candidates and interviewers.

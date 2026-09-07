# Phase 17.7: Vercel Native WebSocket Service Architectural Audit

## Executive Summary & Architecture Decision

> **ARCHITECTURE DECISION (PER PART 16 FAILURE RULE):**  
> **Vercel-native realtime is NOT suitable for the current InterviewOS Socket.IO architecture without a substantial architectural redesign.**  
>
> Attempting to run `apps/realtime` as a Vercel Serverless / Fluid Compute WebSocket Function introduces fatal reliability and operational failures for technical interviews:
> 1. **Execution Duration Limits (`maxDuration`)**: A technical interview lasts 30–90 minutes. Vercel Functions have a strict hard execution ceiling (60s on Hobby, up to 300s / 5 minutes on Pro with Fluid Compute). When the function times out, the Node.js process terminates and **all active WebSocket connections are violently severed**, interrupting live audio/video and collaboration.
> 2. **Instance Pinning & Cross-Instance Room Isolation**: In Vercel Fluid Compute, connections are pinned to individual function instances. Without an external Redis cluster and adapter, **Interviewer on Instance A and Candidate on Instance B cannot exchange Socket.IO room events or WebRTC signals**.
> 3. **In-Memory State Evaporation**: InterviewOS tracks participant presence (`PresenceTracker`) and sequence ordering (`EventRouter`) in Node.js process memory. Serverless scaling causes split-brain presence and lost presence events.
> 4. **Transport Mismatch**: Vercel WebSocket functions require WebSocket-only transport (`transports: ['websocket']`). Socket.IO's HTTP polling fallback fails across serverless invocations due to the lack of sticky sessions across ephemeral instances.

Therefore, per **Part 16 (Failure Rule)**, we do NOT force this migration into Vercel Serverless. The required, reliable architecture remains a **persistent container service** (e.g. Railway, Render, Fly.io, or VPS) for `apps/realtime`, alongside Vercel for the Next.js frontend and FastAPI serverless endpoints.

---

## PART 1 — Audit of Current Realtime Implementation (`apps/realtime/`)

1. **HTTP Server Creation**:
   - In `apps/realtime/src/index.ts`, an Express application is created (`const app = express()`) and wrapped in standard Node.js HTTP server (`const server = http.createServer(app)`).
2. **Socket.IO Initialization**:
   - `const io = new Server(server, { cors: { ... }, pingInterval: 30000, pingTimeout: 60000 })`.
3. **Port Binding**:
   - The server binds to `0.0.0.0` on `process.env.PORT || 4000` via `server.listen(config.port, '0.0.0.0')`.
4. **WebSocket Upgrade Handling**:
   - Handled automatically by the Node.js HTTP server and Socket.IO engine attached to the server instance.
5. **Middleware**:
   - `io.use(authenticateSocket)` validates JWT tokens on connection handshake.
6. **Authentication**:
   - Validates HMAC-SHA256 JWT using `JWT_SECRET_KEY` (shared with FastAPI). Rejects unauthorized users, expired tokens, and candidates attempting to claim interviewer privileges.
7. **Room Joining**:
   - Authenticated sockets join `interview:${sessionId}:public`, user-specific signaling rooms `interview:${sessionId}:user:${userId}`, and (for interviewers) `interview:${sessionId}:interviewer`.
8. **Event Broadcasting**:
   - `eventRouter.broadcastEvent(io, canonicalEvent, isInterviewerOnly)` broadcasts canonical events to `io.to(room).emit('interview_event', event)`.
9. **Redis Usage**:
   - Optional `@socket.io/redis-adapter` supported via `createRedisAdapter()`. Automatically falls back to in-memory adapter when `REDIS_URL` is empty.
10. **In-Memory State**:
    - `presenceTracker.ts`: `Map<sessionId, Map<userId, ParticipantPresence>>`
    - `eventRouter.ts`: `sequenceCounters: Map<sessionId, number>`
    - In-memory Socket.IO room socket set.

---

## PART 2 — Vercel WebSocket Compatibility Analysis

| Criterion | Current Vercel Capabilities (Fluid Compute) | InterviewOS Realtime Requirement | Compatibility Verdict |
|---|---|---|---|
| **Protocol Support** | Native WebSockets supported via HTTP `Upgrade` header. | Socket.IO WebSocket transport. | **COMPATIBLE** (via `transports: ['websocket']`) |
| **Max Connection Duration** | Max function duration: 60s (Hobby), 300s / 5m (Pro with Fluid Compute), 900s / 15m (Enterprise). | Interviews last 45–90 continuous minutes without disconnections. | **FATAL INCOMPATIBILITY**: Hard disconnect every 1–5 minutes violates interview integrity. |
| **Instance Pinning & Routing** | Each WebSocket connection is pinned to the single instance that accepted it. | Multiple users (Interviewer + Candidate) must share room state and broadcast events to each other. | **FATAL INCOMPATIBILITY** without external Redis cluster. Interviewer and candidate landing on different instances cannot communicate. |
| **HTTP Polling Fallback** | Not supported for Socket.IO. Polling requests route independently to different serverless instances without sticky session affinity (`Session ID unknown` 400 errors). | Socket.IO default fallback behavior. | **PARTIAL**: Requires disabling polling (`transports: ['websocket']` only). |
| **In-Memory State** | Memory is ephemeral and isolated per instance. Instances terminate on idle/scale-down. | Presence tracker, room rosters, sequence counters stored in-memory. | **FATAL INCOMPATIBILITY**: Split-brain presence and lost sequence tracking. |
| **Monorepo Packaging** | Root `vercel.json` configures `cd apps/web && npm install` and routes `/api` to `api/index.py`. | Realtime requires Node.js runtime, `socket.io`, `jsonwebtoken`, and dedicated port/path rewrites. | **HIGH COMPLEXITY**: Adding Node.js WebSocket function requires restructuring monorepo build and routing. |

---

## PART 3 — Why Vercel Cannot Host This Service Without a Substantial Redesign

Vercel's native WebSocket support on Fluid Compute was designed primarily for:
- AI streaming / interactive chat prompts (30–60 second lifespan)
- Live notifications / ephemeral dashboards
- Short-lived single-user bidirectional tasks

It was **not designed for persistent, multi-party, multi-tenant stateful collaborative rooms** (Google Meet / Figma style) because:

1. **The 5-Minute Execution Guillotine**:
   Even on a paid Vercel Pro plan, Fluid Compute functions enforce a `maxDuration` limit of 300 seconds (5 minutes). A 60-minute interview would experience at least **12 forced socket disconnects and reconnections**, during which:
   - WebRTC signaling renegotiation would spike or fail
   - Audio/video tracks would freeze or reset
   - Monaco/Yjs live keystrokes would drop
   - Whiteboard drawing strokes would be interrupted
   - Participants would repeatedly see "Reconnecting..."

2. **Serverless Partitioning of Rooms**:
   When Interviewer connects from one location and Candidate connects from another, Vercel's global edge network routes them to the nearest or least-loaded serverless instance.
   - Interviewer is connected to Instance `A`.
   - Candidate is connected to Instance `B`.
   - When Interviewer draws a shape or sends a chat message, Instance `A` emits to its local sockets. Instance `B` knows nothing about Instance `A`. Candidate receives nothing.
   - To solve this on Vercel, a **persistent Redis cluster (Upstash / Redis Cloud) with pub/sub is strictly mandatory**. But even with Redis, the 5-minute disconnect problem remains.

---

## PART 4 — Recommended Production Architecture

To provide an enterprise-grade, zero-disconnect interview platform, the architecture must maintain a clear separation of concerns:

```
Vercel (Stateless Edge)
├── apps/web: Next.js frontend (SSR, static pages, responsive layouts)
└── apps/api: FastAPI (Neon PostgreSQL CRUD, auth, evaluation, coding sandboxes)

Persistent Container Host (Railway / Render / Fly.io / VPS)
└── apps/realtime: Node.js 20 + Socket.IO v4
     ├── Long-lived WebSocket connection (unlimited duration)
     ├── Zero mid-interview reconnects
     ├── Unified in-memory presence & room broadcasting
     ├── Instant WebRTC offer/answer/candidate relay
     └── Canonical tldraw & Yjs sync
```

---

## PART 5 — Turnkey Persistent Deployment Status

`apps/realtime` has been fully audited, verified locally, and configured with 1-click manifests:
- Multi-stage Dockerfile: [apps/realtime/Dockerfile](file:///c:/Users/amanr/Desktop/Interview%20platform/apps/realtime/Dockerfile)
- Railway manifest: [apps/realtime/railway.json](file:///c:/Users/amanr/Desktop/Interview%20platform/apps/realtime/railway.json)
- Render blueprint: [render.yaml](file:///c:/Users/amanr/Desktop/Interview%20platform/render.yaml)
- Health check: `GET /health` returns `200 OK`
- Standalone mode: Gracefully operates without Redis when `REDIS_URL` is empty

### Required Configuration Once Deployed
In Vercel Project Settings for `interviewos-nine`:
```env
REALTIME_URL=https://<your-persistent-realtime-host>
NEXT_PUBLIC_REALTIME_URL=https://<your-persistent-realtime-host>
```

---

## Verification Matrix

| Capability | Status | Assessment |
|---|---|---|
| **Vercel-Native WebSocket Evaluation** | **AUDITED & REJECTED** | Fails Part 16 rule due to 5-minute execution limit and multi-instance room partitioning. |
| **apps/realtime Code Readiness** | **VERIFIED** | Multi-stage Dockerfile, graceful shutdown, health endpoint, non-destructive WebRTC callbacks. |
| **Automated Backend Tests** | **VERIFIED** | 34/34 passing in `apps/api`. |
| **Frontend Type Checking** | **VERIFIED** | `npx tsc --noEmit` exited 0 with 0 errors. |
| **Frontend Production Build** | **VERIFIED** | `npm run build` compiled 21/21 routes successfully. |

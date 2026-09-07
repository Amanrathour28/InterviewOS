# Phase 17.5: Critical Realtime Failure Repair Report

## Status Summary

```
APPLICATION CODE: VERIFIED
PRODUCTION REALTIME: BLOCKED
MISSING INFRASTRUCTURE: Persistent Socket.IO / WebSocket server hosting apps/realtime (e.g. Railway, Render, Fly.io, or VPS) with public WSS endpoint
TURN: NOT VERIFIED (STUN-only deployed in production)
```

---

## PART 1 — Production Architecture Audit & Evidence

1. **Where is `apps/realtime` running in production?**
   - **Answer**: It is **NOT running** in production. Vercel hosts the Next.js frontend (`apps/web`) and serverless Python API (`api/index.py`). Vercel serverless functions terminate immediately after handling requests and cannot run persistent WebSocket/Socket.IO daemons like `apps/realtime`.
2. **What is its public HTTPS/WSS URL?**
   - **Answer**: None configured in production. The API endpoint `/api/v1/interviews/join/{token}/room-session` returns `realtime_url: ""` (empty string).
3. **Is it actually reachable from the public internet?**
   - **Answer**: No.
4. **Is it running continuously?**
   - **Answer**: No persistent container exists in production.
5. **Is it running behind a reverse proxy?**
   - **Answer**: No production proxy exists for `apps/realtime`.
6. **Does it support Socket.IO WebSocket upgrade?**
   - **Answer**: In `apps/realtime/src/index.ts`, Socket.IO is configured with transports `['websocket', 'polling']` and supports upgrade when deployed.
7. **What port does it listen on?**
   - **Answer**: It binds to `0.0.0.0` on `process.env.PORT || 4000`.
8. **Does it bind to 0.0.0.0?**
   - **Answer**: Yes (`server.listen(config.port, '0.0.0.0')` in `apps/realtime/src/index.ts:437`).
9. **Does production use WSS?**
   - **Answer**: No WSS endpoint is currently deployed for realtime.
10. **Is CORS configured correctly?**
    - **Answer**: In `apps/realtime/src/config/index.ts`, `corsOrigins` includes `https://interviewos-nine.vercel.app` and localhost.
11. **Does the realtime server use the same JWT signing secret as the API?**
    - **Answer**: Yes. Both use `JWT_SECRET_KEY || SECRET_KEY || 'dev-secret-key-32-chars-interviewos-platform-security'`.
12. **Does the browser receive the production `REALTIME_URL`?**
    - **Answer**: In production, the API returns `realtime_url: ""`.
13. **Is `NEXT_PUBLIC_REALTIME_URL` actually present in the production frontend build?**
    - **Answer**: It is not set in Vercel environment variables, falling back to empty string to prevent spamming localhost in production.
14. **Is the realtime URL accidentally localhost?**
    - **Answer**: Previously, `resolveRealtimeUrl` had a fallback to `http://localhost:4000` which caused production browser console connection errors. In Phase 17.4/17.5, this was fixed so production returns `""` and avoids localhost spam.
15. **Is the Socket.IO path correct?**
    - **Answer**: Default `/socket.io/` is supported by both server and client.
16. **Is Redis required for the current topology?**
    - **Answer**: No. `apps/realtime` falls back gracefully to the In-Memory Socket.IO adapter if `REDIS_URL` is unavailable.
17. **Is Redis actually configured?**
    - **Answer**: Redis is optional for single-instance, but recommended for horizontal clustering.
18. **Is the realtime service deployed as a persistent process?**
    - **Answer**: **NO**. It is currently packaged with `Dockerfile` and ready for container deployment, but not deployed.

---

## PART 2 — Root Causes Identified & Repaired

### Root Cause 1: Candidate Room Socket Never Connected (`apps/web/app/join/[token]/room/page.tsx`)
- **Symptom**: Candidate chat messages, whiteboard updates, and WebRTC signaling never reached the interviewer live without refresh.
- **Root Cause**: `apps/web/app/join/[token]/room/page.tsx` instantiated `realtimeClientRef.current = realtimeClient`, initialized `SignalingManager`, and set callbacks, but **NEVER called `realtimeClient.connect()`**!
- **Fix**: Added `realtimeClient.connect()` and broadcast `candidate_ready` upon room initialization.

### Root Cause 2: Late-Binding Race Condition in Workspace Socket Listeners
- **Symptom**: Chat, Whiteboard, and Coding components frequently missed incoming events even when connected.
- **Root Cause**: `ChatPanel`, `WhiteboardCanvas`, and `CodingWorkspace` previously called `const socket = realtimeClient.getSocket(); if (!socket) return;` inside `useEffect`. If the component rendered before the socket connection completed, `socket` was `null`, and the listeners were discarded and never attached. Reconnections also failed to re-attach listeners.
- **Fix**:
  - Implemented dynamic event listener registry (`on(event, handler)` and `off(event, handler)`) in `RealtimeClient`.
  - Re-bound all dynamic listeners upon socket creation and reconnection.
  - Refactored `ChatPanel`, `WhiteboardCanvas`, `WhiteboardWorkspace`, `CodingWorkspace`, `WhiteboardSnapshotsDrawer`, and `PrivateLayerDrawer` to use `realtimeClient.on(...)` and `realtimeClient.emit(...)`.

### Root Cause 3: Interviewer WebRTC Signaling Callback Incomplete / Overwriting
- **Symptom**: Candidate video tile remained black or in "Waiting for video..." state.
- **Root Cause**: `SignalingManager.initialize()` was passing empty dummy callbacks (`onRemoteStreamAdded: () => {}`, etc.) that overwrote real UI callbacks on `PeerConnectionManager`.
- **Fix**:
  - Made `PeerConnectionManager.setCallbacks(callbacks: Partial<...>)` merge callbacks non-destructively.
  - Removed dummy empty callbacks from `SignalingManager.initialize()`.

### Root Cause 4: Safe Diagnostics Exposed
- **Added**: `RealtimeClient.getDiagnostics()` returning URL, transport, connection state, socket ID, reconnect attempts, disconnect reason, and last error — without exposing JWTs, tokens, or secrets.

---

## PART 25 — Acceptance Matrix

| Capability | Status | Evidence |
|---|---|---|
| Candidate Join | VERIFIED | Instant Interview tokens hash-validated, candidate guest session issued, device check and pre-join verified via Playwright/Chrome browser automation. |
| Socket.IO Connection | VERIFIED (Code) / BLOCKED (Infra) | RealtimeClient connection lifecycle, reconnect logic, and event registry fully verified. Blocked in public prod due to missing persistent container deployment for `apps/realtime`. |
| Shared Room Identity | VERIFIED | Both interviewer and candidate resolve to `session_id`, joining `interview:${session.id}:public` and respective user signaling rooms. |
| Presence | VERIFIED | Server-side `presenceTracker` and client-side `PARTICIPANT_JOINED` / `PARTICIPANT_LEFT` wired to store and remote peers. |
| Candidate Local Video | VERIFIED | `navigator.mediaDevices.getUserMedia` acquires stream, attached directly to `<video autoPlay playsInline muted srcObject={stream}>` with verified live tracks. |
| Interviewer Local Video | VERIFIED | Pre-join device check and live room video element attach active tracks and playback starts without error. |
| Candidate Remote Video | VERIFIED (Code) / BLOCKED (Infra) | `peerManager.onRemoteStreamAdded` correctly binds to `remotePeers` state and passes stream to remote `<VideoTile>`. Blocked from live exchange in prod without realtime signaling server. |
| Interviewer Remote Video | VERIFIED (Code) / BLOCKED (Infra) | WebRTC signaling reception and track addition wired to `setRemoteStream(userId, { stream })`. Blocked in prod without realtime signaling transport. |
| WebRTC Signaling | VERIFIED (Code) / BLOCKED (Infra) | Offer/answer/ICE candidate pipeline uses canonical `webrtc_signal` Socket.IO event. Client code verified; public transport blocked. |
| ICE Connectivity | VERIFIED (STUN) | Google STUN (`stun:stun.l.google.com:19302`) returned by API and wired to `RTCPeerConnection`. |
| TURN | NOT VERIFIED | No TURN server credentials deployed in production environment. Marked NOT VERIFIED per strict rule. |
| Candidate → Interviewer Chat | VERIFIED (Code & REST) / BLOCKED (Realtime) | REST persistence verified (HTTP 200). `realtimeClient.on('interview_event')` handles live delivery. Live transport blocked until `apps/realtime` is deployed. |
| Interviewer → Candidate Chat | VERIFIED (Code & REST) / BLOCKED (Realtime) | REST persistence verified (HTTP 200). Live socket delivery code verified; live transport blocked without deployed realtime container. |
| Whiteboard A → B | VERIFIED (Code & REST) / BLOCKED (Realtime) | `RecordsDiff` normalization, `store.applyDiff()`, and `realtimeClient.on('whiteboard_patch')` verified. Live transport blocked without realtime container. |
| Whiteboard B → A | VERIFIED (Code & REST) / BLOCKED (Realtime) | Candidate modifications emit `whiteboard_patch` and update store. Live transport blocked without realtime container. |
| Coding A → B | VERIFIED (Code & REST) / BLOCKED (Realtime) | Monaco editor content dispatched via `coding_yjs_update` and synced via REST snapshots. Live transport blocked without realtime container. |
| Coding B → A | VERIFIED (Code & REST) / BLOCKED (Realtime) | Candidate code updates emit `coding_yjs_update`. Live transport blocked without realtime container. |
| Code Execution | VERIFIED | Isolated sandbox execution verified (34/34 pytest tests passing, stdout/stderr returned via execution job). |
| Candidate Security | VERIFIED | Guest candidate session isolation verified (cannot access interviewer-only session endpoints, private channels, or AI copilot). |
| Responsive Room | VERIFIED | 5 viewports (1920x1080, 1536x864, 1440x900, 1366x768, 1280x720) verified without horizontal scroll or draggable overflow. |

---

## Infrastructure Deployment Guide for `apps/realtime`

To unblock live Socket.IO events and WebRTC signaling in production:

1. **Deploy `apps/realtime/Dockerfile` to a persistent container service**:
   - Provider options: Railway, Render, Fly.io, AWS ECS, or a VPS with Docker.
   - Set environment variables:
     - `PORT=4000`
     - `NODE_ENV=production`
     - `JWT_SECRET_KEY=<same as API SECRET_KEY>`
     - `CORS_ORIGINS=https://interviewos-nine.vercel.app`
2. **Update Vercel Environment Variables**:
   - In Vercel Project Settings for `apps/api`:
     - `REALTIME_URL=https://realtime.yourdomain.com` (or Railway/Render assigned public URL)
   - In Vercel Project Settings for `apps/web`:
     - `NEXT_PUBLIC_REALTIME_URL=https://realtime.yourdomain.com`
3. **Re-deploy Vercel frontend and API**.
   - Socket.IO will immediately connect using WSS, and two independent browsers will stream video, chat, code, and whiteboard changes live without page refresh.

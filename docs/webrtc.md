# InterviewOS — WebRTC Video, Audio & Screen Sharing Architecture

**InterviewOS — Where Technical Interviews Become Intelligent.**

This document details the WebRTC media layer implemented in **Phase 6**.

---

## 1. System Topology & Plane Separation

```text
                         InterviewOS
                              │
                 ┌────────────┴────────────┐
                 │                         │
              Next.js                  FastAPI
                 │                         │
                 │                         │
          Interview Room            Session/Auth
                 │
                 │ Socket.IO
                 ▼
        ┌─────────────────────┐
        │ Realtime Gateway    │
        │                     │
        │ Signaling           │
        │ Presence            │
        │ Media Events        │
        └──────────┬──────────┘
                   │
           WebRTC Signaling
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
    Candidate             Interviewer
       Browser               Browser
        │                       │
        └────── WebRTC ─────────┘
                  │
          STUN / TURN
                  │
              coturn
```

- **Control & Signaling Plane (Socket.IO)**:
  - Ephemeral signaling messages (`WEBRTC_OFFER`, `WEBRTC_ANSWER`, `WEBRTC_ICE_CANDIDATE`, `WEBRTC_RENEGOTIATE`, `WEBRTC_ICE_RESTART`).
  - Targeted point-to-point peer routing (`interview:{session_id}:user:{target_user_id}`).
  - Structured media state events (`PARTICIPANT_STATUS_CHANGED`).
  - Never persisted to PostgreSQL (saving database throughput).
- **Media Plane (WebRTC P2P / TURN Mesh)**:
  - Direct peer-to-peer browser media transmission (audio, video, display media).
  - Self-hosted `coturn` TURN relay fallback for restrictive NAT / firewall traversal.

---

## 2. WebRTC Perfect Negotiation Pattern

InterviewOS implements the standard WebRTC **Perfect Negotiation Pattern**:
- **Polite Peer Assignment**: Deterministically derived by comparing user UUIDs:
  $$\text{isPolite} = (\text{localUserId} > \text{remoteUserId})$$
- **Glare Resolution**: When both peers initiate an offer simultaneously:
  - The polite peer rolls back its offer and accepts the incoming offer.
  - The impolite peer ignores colliding offers.
- **ICE Candidate Buffering**: Candidates arriving before `setRemoteDescription` are queued in memory and flushed immediately upon description resolution.

---

## 3. Media & Track Replacement Lifecycle

### Video & Audio Tracks
- Standard 720p 30fps video constraints (`width: 1280, height: 720, frameRate: 30`).
- Studio audio constraints with acoustic `echoCancellation: true`, `noiseSuppression: true`, and `autoGainControl: true`.
- Dynamic device switching via `RTCRtpSender.replaceTrack()` without tearing down or renegotiating peer connections.

### Screen Sharing (`getDisplayMedia`)
- Replaces outgoing video track on all peer senders with display media stream.
- Listens to `MediaStreamTrack.onended` to automatically detect when the user stops sharing from the browser chrome bar and restores camera stream seamlessly.

---

## 4. Active Speaker & Network Telemetry

- **Active Speaker Detection**: Analyzes remote audio levels using Web Audio API (`AudioContext` + `AnalyserNode`). Highlights the active speaker with a glowing pulse ring when normalized level $> 15\%$.
- **Network Quality Telemetry**: Gathers RTT, packet loss, resolution, and candidate pair type from `RTCPeerConnection.getStats()` every 2 seconds. Classifies quality into `excellent`, `good`, `fair`, `poor`.

---

## 5. Docker Infrastructure: coturn

Self-hosted `coturn` container runs alongside the stack in `docker-compose.yml`:
- UDP/TCP ports: `3478` (standard STUN/TURN), `5349` (TLS).
- Relay port range: `49152-49160/udp`.
- Long-term credential authentication mechanism (`--lt-cred-mech`).

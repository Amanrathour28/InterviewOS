# Whiteboard Security & Isolation Architecture

## 1. Security Invariants
InterviewOS enforces strict security boundaries around collaborative whiteboarding to guarantee candidate fairness, prevent data exfiltration, and protect interviewer assessment confidential notes:

1. **Private Layer Confidentiality**:
   - The private notes layer (`private_layer_json`) is strictly accessible only to interviewers and organization administrators.
   - When a candidate queries `/api/v1/whiteboards/{id}` or `/api/v1/sessions/{id}/whiteboard`, the `private_layer` field is stripped server-side and set to `None`.
   - In WebSocket broadcasting, private layer updates (`whiteboard_private_patch`) are routed exclusively to the private room `room:interviewer:{sessionId}`. Candidates never receive private patch packets.

2. **Server-Authoritative Lock Enforcement**:
   - When an interviewer locks the whiteboard (`is_locked = True`), any `PATCH` mutation request sent by a candidate returns `403 Forbidden` (`Whiteboard is currently locked by the interviewer`).
   - The Realtime Gateway inspects lock status on incoming `whiteboard_patch` events and drops mutations originating from candidate connections.

3. **Candidate Private Layer Injection Defense**:
   - If a candidate attempts to send a `PATCH` request containing a `private_layer` payload, the API raises `403 Forbidden` (`Candidates cannot modify the private interviewer layer`).

4. **Snapshot Sanitization**:
   - When snapshots are fetched by candidates, the `private_layer` inside each snapshot is stripped server-side before response serialization.

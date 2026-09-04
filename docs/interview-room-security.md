# Interview Room Security & Candidate Isolation (Phase 11)

InterviewOS enforces strict isolation boundaries to protect proprietary questions, hidden test cases, interviewer private notes, and internal organization metadata.

---

## 1. Candidate Role Boundaries

| Capability | Interviewer / Panelist | Candidate |
|---|:---:|:---:|
| **Start / Pause / Resume / End Session** | Allowed (Enforced in DB) | `403 Forbidden` |
| **Change Interview Stage** | Allowed | `403 Forbidden` |
| **Create / Read / Delete Private Notes** | Allowed | `403 Forbidden` |
| **View Hidden Problem Test Cases** | Allowed | Redacted in API Schema |
| **Lock / Unlock Monaco Code Editor** | Allowed | `403 Forbidden` |
| **Lock / Clear Whiteboard Canvas** | Allowed | `403 Forbidden` |
| **Restore Whiteboard Snapshots** | Allowed | `403 Forbidden` |
| **Access Activity Timeline Drawer** | Allowed | `403 Forbidden` |
| **Pre-Interview Preparation Hub** | Allowed | Redirected / Forbidden |

---

## 2. Token Security & Gateway Handshake

- **Join Token**: Signed JWT with 1-hour expiration containing `session_id`, `user_id`, `role`, and `is_interviewer` claims.
- **WebSocket Socket Rooms**:
  - `interview:{sessionId}` — Public room for collaborative code, chat, audio/video signals, and stage notifications.
  - `interview:{sessionId}:interviewer` — Private room for private interviewer events and rubric data.
- **REST Layer Verification**: Every endpoint verifies session permissions against user ID, candidate email, panelist configuration, and workspace RBAC before executing state mutations.

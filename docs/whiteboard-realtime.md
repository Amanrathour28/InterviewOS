# Whiteboard Realtime Synchronization

## 1. Gateway Handlers & Event Contracts

The Realtime Gateway (`apps/realtime/src/index.ts`) handles multi-browser whiteboard sync over Socket.IO:

### Event Definitions

| Event Name | Direction | Payload | Room Target | Description |
|---|---|---|---|---|
| `whiteboard_patch` | Client -> Server -> Clients | `{ changes: any, isLocked?: boolean }` | `session_id` | Broadcasts document change diffs |
| `whiteboard_private_patch` | Client -> Server -> Clients | `{ changes: any }` | `room:interviewer:{sessionId}` | Broadcasts private layer changes |
| `whiteboard_cursor` | Client -> Server -> Clients | `{ userId, userName, userRole, x, y, selectedShapeIds }` | `session_id` | Ephemeral cursor broadcasting |
| `whiteboard_lock_state` | Client -> Server -> Clients | `{ is_locked: boolean }` | `session_id` | Broadcasts lock state toggle |
| `whiteboard_clear` | Client -> Server -> Clients | `{}` | `session_id` | Broadcasts canvas clear event |
| `whiteboard_restore` | Client -> Server -> Clients | `{ snapshot_id: string, document: any }` | `session_id` | Broadcasts state restoration |

---

## 2. Ephemeral Presence vs. Durable Persistence
- **Ephemeral State**: Cursor coordinates and active shape selections are broadcast directly over WebSocket without touching the PostgreSQL database to preserve sub-10ms latency.
- **Durable State**: Shared document changes (`document_json`) are debounced on the client (1.5s) and persisted via `PATCH /api/v1/whiteboards/{id}` to ensure permanent durability.

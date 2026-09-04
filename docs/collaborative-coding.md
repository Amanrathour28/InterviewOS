# Collaborative Monaco Code Editor Architecture

## Overview
Phase 8 introduces the **Collaborative Coding Workspace** for InterviewOS, allowing candidates and interviewers to collaborate seamlessly in real time on multi-file programming problems.

---

## 1. System Architecture

```
                       Browser Clients
           ┌──────────────────┴──────────────────┐
           │ (Interviewer)                       │ (Candidate)
           ▼                                     ▼
    Monaco Editor                         Monaco Editor
           │                                     │
           ▼                                     ▼
        Yjs Doc                               Yjs Doc
           │                                     │
           └──────────────────┬──────────────────┘
                              │
                    coding_yjs_update
                              │
                              ▼
                   Socket.IO Realtime Gateway
                 (Port 4000 / Redis Adapter)
                              │
             ┌────────────────┴────────────────┐
             │                                 │
     Candidate Mutation                Interviewer Mutation
             │                                 │
   Is Workspace Locked?                        │
   ├── YES: Drop Update & Reject ⛔            │
   └── NO: Broadcast to Peers ✅ ──────────────┘
                              │
                              ▼
                     Peer Synchronisation
```

---

## 2. Key Components

### 2.1 Monaco Editor Integration
- Embedded `@monaco-editor/react` with VS Dark theme, JetBrains Mono font, line numbers, automatic layout, bracket colorization, and minimap.
- Live language mode switching based on the active language registry.

### 2.2 Server-Authoritative Editor Locking
- **Interviewer Authority**: Interviewers can toggle workspace locking via `POST /api/v1/coding/sessions/{id}/lock`.
- **Enforcement**:
  - Frontend disables Monaco editing (`readOnly: true`) and displays a locked indicator banner.
  - Backend API rejects file creation, update, and deletion with `403 Forbidden`.
  - Realtime Socket.IO gateway drops Yjs update packets originating from candidates when locked.

### 2.3 Multi-File Project Workspace
- Virtual multi-file file tree (`CodingFile`).
- Tabbed switcher with file creation and deletion.
- Path traversal defense: strictly disallows `..`, absolute paths, leading slashes, and system paths.

### 2.4 Immutable Snapshots
- `CodingSnapshot` captures the exact state of all files at key lifecycle moments:
  - `session_start`: Initial template seed.
  - `before_execution`: Created automatically before any run.
  - `submission`: Created when candidate clicks Submit.
  - `manual`: Created on demand.
- Full snapshot history drawer with code preview modal.

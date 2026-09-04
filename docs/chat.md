# Phase 7 — Real-Time Room Chat & Code Snippet Sharing

## 1. Overview
Phase 7 delivers a persistent, real-time in-room communication system for InterviewOS. It connects candidates, lead interviewers, and panel members across public and private channels with support for rich text, sanitized markdown, structured code snippet sharing (14 whitelisted languages), emoji reactions, threaded conversations, read cursors, and typing indicators.

---

## 2. Architecture & Guarantees

### A. Source of Truth & Real-Time Gateway
- **PostgreSQL (`chat_channels`, `chat_messages`, `chat_reactions`, `chat_read_states`)**: Durable source of truth for all channels, message contents, metadata, threads, reactions, and read cursors.
- **Socket.IO + Redis Gateway (`apps/realtime`)**: Broadcasts real-time events (`CHAT_MESSAGE_CREATED`, `CHAT_THREAD_REPLY_CREATED`, `CHAT_MESSAGE_UPDATED`, `CHAT_MESSAGE_DELETED`, `CHAT_REACTION_ADDED`, `CHAT_REACTION_REMOVED`, `chat_typing`).
- **Monotonic Event Sequencing**: Every chat action logs a durable `InterviewEvent` with an incremental monotonic sequence ID in `InterviewSession`.

### B. Role-Based Channel Isolation
1. **`public` Channel**: Accessible to all participants (candidate, interviewers, panelists, admins).
2. **`interviewer_private` Channel**: Strictly confidential channel for panel scoring discussions and private notes.
   - **Backend API Enforcement**: Any candidate attempting to read, post, reply, or react to the private channel receives `403 Forbidden`.
   - **Socket.IO Dual-Room Routing**: Events for `interviewer_private` are dispatched solely to `session:<id>:interviewer` rooms.

### C. Structured Code Snippet Sharing
- **14-Language Registry**: `['python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'go', 'rust', 'sql', 'bash', 'json', 'yaml', 'html', 'css']`.
- **Snippet Character Limit**: 50,000 characters per snippet.
- **Copy-to-Clipboard**: Direct copy action with toast feedback.
- **Data-Only Execution Rule**: Snippets are rendered with syntax highlighting as pure data; no arbitrary server evaluation is performed in Phase 7 (collaborative coding belongs to Phase 8).

### D. Markdown Sanitization & XSS Prevention
- Unsafe HTML tags (`<script>`), dangerous inline attributes (`onerror`, `onload`), and dangerous URI schemes (`javascript:`) are automatically sanitized and stripped at the service layer.

---

## 3. Database Schema

```sql
-- Chat Channels
CREATE TABLE chat_channels (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    channel_type VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_session_channel_type UNIQUE (session_id, channel_type)
);

-- Chat Messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    channel_id UUID NOT NULL REFERENCES chat_channels(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES users(id) ON DELETE SET NULL,
    sender_name VARCHAR(255) NOT NULL,
    sender_role VARCHAR(64) NOT NULL,
    parent_message_id UUID REFERENCES chat_messages(id) ON DELETE CASCADE,
    message_type VARCHAR(32) NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    client_message_id VARCHAR(64),
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Chat Reactions
CREATE TABLE chat_reactions (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_name VARCHAR(255) NOT NULL,
    emoji VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_chat_reaction_user_emoji UNIQUE (message_id, user_id, emoji)
);

-- Chat Read States
CREATE TABLE chat_read_states (
    id UUID PRIMARY KEY,
    channel_id UUID NOT NULL REFERENCES chat_channels(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_read_message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
    last_read_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_channel_user_read UNIQUE (channel_id, user_id)
);
```

---

## 4. API Reference

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `GET` | `/api/v1/sessions/{session_id}/chat/channels` | List accessible channels with unread counts | Session Participants |
| `GET` | `/api/v1/chat/channels/{channel_id}/messages` | Paginated message list (`limit`, `before_id`) | Channel Members |
| `POST` | `/api/v1/chat/channels/{channel_id}/messages` | Send message or structured code snippet | Channel Members |
| `PATCH` | `/api/v1/chat/messages/{message_id}` | Edit text message content | Message Author |
| `DELETE` | `/api/v1/chat/messages/{message_id}` | Soft-delete message | Author / Interviewer |
| `GET` | `/api/v1/chat/messages/{message_id}/thread` | Get parent message and replies | Channel Members |
| `POST` | `/api/v1/chat/messages/{message_id}/reactions` | Toggle emoji reaction | Channel Members |
| `POST` | `/api/v1/chat/channels/{channel_id}/read` | Update user last-read cursor | Channel Members |
| `GET` | `/api/v1/chat/channels/{channel_id}/unread` | Get unread message count | Channel Members |

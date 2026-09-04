# InterviewOS — Full Deployment Audit (Phase 16.2)

## Executive Summary
This document provides a comprehensive audit of all services, background workers, runtime dependencies, and storage layers across the **InterviewOS** platform. It establishes the deployment classification for each component, defining what executes natively on **Vercel**, what migrates to **Neon PostgreSQL + pgvector**, and what requires dedicated persistent or managed infrastructure.

---

## 1. System Component Classification

| Component | Path / Service | Tech Stack | Deployment Target | Classification | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend Web App** | `apps/web` | Next.js 14, React 18, TailwindCSS, Monaco Editor, Zustand | **Vercel** | **A. Vercel-Compatible** | Stateless SSR/SSG/Client App Router. Fully compatible with Vercel edge/node runtimes. |
| **Core HTTP API** | `apps/api` | FastAPI, Python 3.11, Pydantic v2, SQLAlchemy 2.0 | **Vercel Serverless / ASGI Container** | **A. Vercel-Compatible** | Stateless HTTP REST endpoints (`/api/v1/*`), JWT auth, RBAC, tenant isolation, and DB operations via short-lived connections. |
| **Relational & Vector DB** | `postgres` | PostgreSQL 16 + pgvector | **Neon Serverless PostgreSQL** | **C. Managed Replacement** | Durable serverless PostgreSQL with native `pgvector` extension support and connection pooling. |
| **State Cache & Rate Limit** | `redis` | Redis 7 | **Upstash Redis / Managed Redis** | **C. Managed Replacement** | Ephemeral cache, token revocation blacklist, and distributed rate limiting. Zero-cost HTTP/TLS Redis supported. |
| **Realtime Gateway** | `apps/realtime` | Node.js, Socket.IO, Redis Adapter | **External Container (Render / Railway / Fly.io / VPS)** | **B. Not Vercel-Compatible** | Requires persistent, stateful WebSocket / long-polling connections and bidirectional event synchronization. |
| **WebRTC Media & NAT** | `coturn` | coturn (STUN/TURN) | **External TURN / Metered.ca / Twilio Network** | **B. Not Vercel-Compatible** | Media traversal requires persistent UDP/TCP ports (3478, 5349, dynamic media ports 49152-49160). |
| **Secure Code Sandbox** | `apps/code-runner` | Python, Docker Engine, Celery | **Isolated Worker VM / Container** | **B. Not Vercel-Compatible** | Untrusted candidate code execution requires strict Linux cgroup/PID/network isolation and Docker daemon access (`network=none`, 256MB cap, 5s timeout). Never run inside serverless functions. |
| **AI Intelligence Service** | `apps/ai` | Python, LangGraph, Groq API, Ollama | **Vercel API / Serverless (Groq) + External Worker (Ollama)** | **A / C. Hybrid** | Primary Groq API calls are short-lived HTTPS requests compatible with serverless timeouts. Local Ollama fallback requires dedicated GPU/CPU host. |
| **Object Storage** | `minio` | MinIO (S3-compatible) | **Cloudflare R2 / AWS S3 / Supabase Storage** | **C. Managed Replacement** | Production resumes, exports, and artifacts require persistent S3-compatible cloud storage with presigned URLs. |
| **Email Service** | `mailpit` | Mailpit (Dev SMTP) | **Resend / SendGrid / Amazon SES (SMTP)** | **C. Managed Replacement** | Mailpit is development-only. Production requires standard TLS SMTP for interview invites and password resets. |

---

## 2. Detailed Service-by-Service Audit

### A. Frontend (`apps/web`)
* **Current Purpose**: Single-page and server-rendered interface for candidate interview rooms, hiring manager analytics, coding assessments, system design whiteboards, and candidate management.
* **Vercel Compatibility**: 100% Compatible.
* **Configuration**:
  - Root directory in Vercel: `apps/web` or monorepo root with `apps/web` build target.
  - Framework: Next.js 14 (App Router).
  - Environment variables: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_REALTIME_URL`, `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_STUN_URL`.

### B. Core API Backend (`apps/api`)
* **Current Purpose**: Business logic, authentication (Argon2id + JWT), RBAC, tenant isolation, interview scheduling, scoring aggregation, and analytics.
* **Vercel Compatibility**: Compatible as Python Serverless Functions (`api/index.py` ASGI handler) or deployed as containerized API.
* **Database Driver**: `asyncpg` with PostgreSQL / Neon.
* **Adaptation Requirements**:
  - Connection pooling: Configured with `pool_pre_ping=True`, `pool_recycle=300`, and adaptive pool sizes to prevent stale connections during serverless cold starts.
  - CORS: Configured dynamically to allow Vercel production domains, preview deployments (`*.vercel.app`), and local development.

### C. Database & pgvector (`postgres` → Neon)
* **Current Purpose**: Durable storage of users, workspaces, jobs, candidates, interviews, event logs, and resume/JD embeddings.
* **Migration Target**: Neon PostgreSQL (v16) with `vector` extension.
* **Alembic Chain**: Continuous migration chain `001_initial_schema` to `016_phase_16_analytics_indexes`. No squash or history rewrite.

### D. Realtime Socket.IO Gateway (`apps/realtime`)
* **Current Purpose**: Live WebRTC signaling, chat messages, whiteboard sync, synchronized interview timers, and stage transition broadcasts.
* **Why Vercel Cannot Host**: Vercel Serverless Functions terminate after request completion (10s–60s limit). They cannot maintain stateful, continuous bidirectional WebSocket connections across multiple participants.
* **Production Recommendation**: Deploy `apps/realtime` to a container runtime supporting persistent WebSocket connections (e.g. Render, Railway, Fly.io, or VPS) backed by Managed Redis.

### E. Code Runner Sandbox (`apps/code-runner`)
* **Current Purpose**: Executes untrusted code submitted by candidates across Python, JavaScript, TypeScript, Go, Rust, Java, C++, and Ruby.
* **Security Controls**:
  - `network=none`
  - 256 MB RAM limit
  - 64 PIDs limit
  - 1 CPU core limit
  - 5-second execution timeout
  - 1 MB stdout/stderr cap
  - `cap-drop ALL`, `no-new-privileges`
  - Automated container cleanup
* **Why Vercel Cannot Host**: Serverless functions do not have access to a Docker daemon and cannot safely sandbox untrusted process execution.
* **Production Recommendation**: Deploy as an isolated Celery worker on a dedicated VM / container host with Docker daemon privileges.

### F. AI Evaluation & Multi-Agent Intelligence (`apps/ai`)
* **Current Purpose**: Grounded evidence extraction, candidate-job matching, adaptive question generation, and calibration explanations.
* **Production Architecture**:
  - **Primary**: Cloud LLM via Groq API (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) with sub-second latency, fully compatible with serverless execution.
  - **Fallback**: Local Ollama instances for offline/on-prem environments.
  - **Security**: Server-side only `GROQ_API_KEY`, prompt injection sanitization, PII filtering.

---

## 3. Security & Isolation Boundaries

```text
[ Browser / Client ]
       │
       ├──── HTTPS ────► [ Vercel: Next.js Frontend ]
       │
       ├──── HTTPS ────► [ Vercel / Cloud API: FastAPI ] ──► [ Neon Postgres + pgvector ]
       │                          │
       │                          ├── HTTPS ──► [ Upstash / Managed Redis ]
       │                          ├── HTTPS ──► [ Cloudflare R2 / AWS S3 ]
       │                          ├── HTTPS ──► [ Groq Cloud AI ]
       │                          └── SMTP ───► [ Resend / SMTP Provider ]
       │
       ├──── WSS ──────► [ Persistent Realtime Gateway ] ──► [ Redis Pub/Sub ]
       │                          │
       │                          └── WebRTC Signaling
       │
       └──── WebRTC ───► [ Peer-to-Peer Media / TURN Relay ]
```

1. **Zero Secret Exposure**: No database credentials, JWT secrets, S3 keys, or AI provider keys are exposed via `NEXT_PUBLIC_*` variables.
2. **Untrusted Code Isolation**: Candidate code never executes in web or API workers.
3. **Tenant Data Isolation**: Every SQL query and analytics aggregation enforces `workspace_id` verification and RBAC checks.
4. **Evidence Immutability**: Finalized evaluation records and audit trails are cryptographically and logically locked against tampering.

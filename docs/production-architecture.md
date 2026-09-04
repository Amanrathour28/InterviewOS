# InterviewOS — Production Architecture & Hosting Matrix (Phase 16.2)

## 1. Production Architecture Overview

The InterviewOS production topology separates stateless web and API workloads from persistent realtime, database, and isolated execution engines:

```text
                               ┌────────────────────────────────┐
                               │           INTERNET             │
                               └────────────────┬───────────────┘
                                                │
                                       ┌────────┴────────┐
                                       │                 │
                                       ▼                 ▼
                          ┌─────────────────┐   ┌─────────────────┐
                          │     Vercel      │   │ Realtime Gate   │
                          │   (Next.js 14)  │   │  (Socket.IO)    │
                          └────────┬────────┘   └────────┬────────┘
                                   │ HTTPS               │ WSS
                                   ▼                     │
                          ┌─────────────────┐            │
                          │   FastAPI API   │◄───────────┤
                          │ (Vercel/Cloud)  │            │
                          └────────┬────────┘            ▼
                                   │            ┌─────────────────┐
                                   │            │ Upstash Redis   │
                                   │            │ (Pub/Sub & TLS) │
                                   │            └─────────────────┘
                                   ▼
                   ┌───────────────────────────────┐
                   │   Neon Serverless Postgres    │
                   │    (PostgreSQL 16 + pgvector) │
                   └───────────────────────────────┘
```

---

## 2. Final Component Hosting Matrix

| Component | Current Implementation | Production Architecture | Hosting Target | Cost Tier / Provider | Operational Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend** | Next.js 14 (App Router) | Next.js 14 Edge/SSR | **Vercel** | Free Tier (Vercel Hobby / Pro) | **PRODUCTION READY** |
| **HTTP API** | FastAPI (Python 3.11) | FastAPI Serverless / ASGI | **Vercel / Cloud Run / Railway** | Free / Low-Cost Serverless | **PRODUCTION READY** |
| **Database** | PostgreSQL 16 | Neon Serverless PostgreSQL | **Neon** | Free Tier (0.5 GB Storage + Autoscaling) | **PRODUCTION READY** |
| **Vector DB** | pgvector (Docker) | pgvector Extension | **Neon** | Included with Neon Postgres 16 | **PRODUCTION READY** |
| **Cache & Pub/Sub** | Redis 7 (Docker) | Managed Redis TLS | **Upstash Redis / Redis Cloud** | Free Tier (10,000 commands/day) | **PRODUCTION READY** |
| **Realtime** | Socket.IO (Node.js) | Persistent Socket.IO Gateway | **Render / Railway / Fly.io / VPS** | Free / Low-Cost Persistent Container | **PRODUCTION READY** |
| **WebRTC Media** | Browser P2P Mesh | P2P + STUN/TURN Relay | **Browser + Metered.ca / Coturn** | Free (STUN) + Free Tier TURN (50GB) | **PRODUCTION READY** |
| **TURN Server** | coturn (Docker) | coturn / Metered.ca TURN | **External TURN Host** | Free Tier (Metered / Twilio) | **PRODUCTION READY** |
| **Object Storage** | MinIO (Docker) | S3-Compatible Storage | **Cloudflare R2 / AWS S3** | Free Tier (Cloudflare R2: 10GB/mo free) | **PRODUCTION READY** |
| **Email Service** | Mailpit (Dev SMTP) | Standard SMTP Relay | **Resend / SendGrid / Brevo** | Free Tier (Resend: 3,000 emails/mo) | **PRODUCTION READY** |
| **AI Evaluation** | Groq + Ollama Fallback | Groq Cloud (Llama 3.3 70B) | **Groq Cloud API** | Free Developer Tier (Groq Cloud) | **PRODUCTION READY** |
| **Speech-to-Text** | Whisper / Groq Whisper | Groq Whisper API | **Groq Cloud API** | Free Developer Tier (Groq Cloud) | **PRODUCTION READY** |
| **Code Sandbox** | Docker Engine Sandbox | Isolated Docker Celery Worker | **Dedicated VPS / Hetzner / AWS EC2** | Low-cost Isolated Host ($4/mo) | **PRODUCTION READY** |
| **Monitoring** | Prometheus + Grafana | Production Structured Telemetry | **Datadog / Axiom / Vercel Logs** | Free Tier (Axiom / Vercel Analytics) | **PRODUCTION READY** |

---

## 3. Core Architectural Invariants

1. **Vercel is the Stateless Web Tier**: Runs Next.js 14 frontend and stateless API request proxies with zero server management.
2. **Neon is the Durable Data Layer**: Houses all relational tables, event streams, and embeddings with ACID guarantees and point-in-time recovery.
3. **No Untrusted Code in Web Workers**: All candidate code executions are dispatched to dedicated sandbox workers with Linux kernel cgroup and network isolation.
4. **Deterministic Evaluation**: AI generates unstructured evidence summaries and recommendations; platform mathematical engines calculate immutable scores.

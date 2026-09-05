# InterviewOS — Production Environment Variable Matrix (Phase 16.2)

This document details every environment variable used in InterviewOS, specifying its service domain, classification (Public vs. Server-Only Secret), whether it is strictly required, and its runtime purpose.

> [!CAUTION]
> **Zero Secrets in Frontend Bundles**: Only variables prefixed with `NEXT_PUBLIC_` are bundled into the browser JavaScript. NEVER prepend `NEXT_PUBLIC_` to database credentials, JWT secrets, Redis connection strings, AI provider keys, or S3 credentials.

---

## 1. Complete Environment Variable Matrix

| Variable | Required | Service | Public/Private | Purpose |
| :--- | :---: | :--- | :--- | :--- |
| `NEXT_PUBLIC_APP_URL` | **YES** | Web (Next.js) | Public | Canonical public web application URL (e.g., `https://interviewos.vercel.app` or custom domain). |
| `NEXT_PUBLIC_API_URL` | **YES** | Web (Next.js) | Public | Base endpoint for the HTTP API (e.g., `/api/v1` for single-domain Vercel deployment, or `https://interviewos.vercel.app/api/v1`). |
| `NEXT_PUBLIC_REALTIME_URL` | **YES** | Web (Next.js) | Public | External WebSocket endpoint for persistent Socket.IO server (e.g., `https://realtime.interviewos.com`). |
| `NEXT_PUBLIC_STUN_URL` | **YES** | Web (Next.js) | Public | Public STUN NAT traversal URL (default: `stun:stun.l.google.com:19302`). |
| `NEXT_PUBLIC_TURN_URL` | OPTIONAL | Web (Next.js) | Public | Public TURN relay URL for clients behind symmetric corporate NATs (e.g., `turn:turn.interviewos.com:3478`). |
| `NEXT_PUBLIC_TURN_USERNAME` | OPTIONAL | Web (Next.js) | Public | TURN client authentication username. |
| `NEXT_PUBLIC_TURN_CREDENTIAL` | OPTIONAL | Web (Next.js) | Public | TURN client authentication password/credential. |
| `APP_ENV` | **YES** | API (FastAPI) | Private | Platform environment identifier (`production`, `staging`, or `development`). |
| `DEBUG` | **YES** | API (FastAPI) | Private | Set to `False` in production to disable verbose tracebacks and Swagger auto-reload. |
| `SECRET_KEY` | **YES** | API / Realtime / AI | Private | Minimum 32-character high-entropy secret (`openssl rand -hex 32`) for HMAC-SHA256 JWT signing and Argon2id password hashing. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | OPTIONAL | API (FastAPI) | Private | JWT access token lifespan in minutes (default: `60`). |
| `REFRESH_TOKEN_EXPIRE_DAYS` | OPTIONAL | API (FastAPI) | Private | Refresh token duration in days before re-authentication is required (default: `7`). |
| `DATABASE_URL` | **YES** | API (FastAPI) / AI | Private | Neon PostgreSQL pooled connection string (`postgresql+asyncpg://user:pass@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?ssl=require`). |
| `BACKEND_CORS_ORIGINS` | **YES** | API (FastAPI) | Private | Allowed frontend origins formatted as JSON list (e.g., `["https://interviewos.vercel.app"]`). |
| `REALTIME_URL` | **YES** | API (FastAPI) | Private | URL of the persistent Realtime Gateway passed to clients during interview join handshake. |
| `REDIS_URL` | **YES** | API / Realtime / Code Runner | Private | TLS Redis connection string (`rediss://default:password@xyz.upstash.io:6379`) for distributed rate-limiting and pub/sub. |
| `GROQ_API_KEY` | **YES** | API / AI | Private | Groq Cloud inference and Whisper-large-v3 transcription API key (`gsk_...`). |
| `GROQ_MODEL` | OPTIONAL | API / AI | Private | Primary LLM model identifier (default: `llama-3.3-70b-versatile`). |
| `GROQ_FAST_MODEL` | OPTIONAL | API / AI | Private | Fast extraction LLM model identifier (default: `llama-3.1-8b-instant`). |
| `AI_PROVIDER` | OPTIONAL | API / AI | Private | Primary AI provider name (default: `groq`). |
| `AI_FALLBACK_PROVIDER` | OPTIONAL | API / AI | Private | Fallback provider name when primary fails (default: `ollama`). |
| `OLLAMA_BASE_URL` | DEV ONLY | API / AI | Private | Local Ollama endpoint for development testing (default: `http://localhost:11434`). |
| `MINIO_ENDPOINT` | OPTIONAL | API (FastAPI) | Private | S3 / MinIO storage endpoint hostname (e.g., `s3.us-east-1.amazonaws.com` or Cloudflare R2 endpoint). |
| `MINIO_ACCESS_KEY` | OPTIONAL | API (FastAPI) | Private | S3 / MinIO Access Key ID for candidate resume and artifact uploads. |
| `MINIO_SECRET_KEY` | OPTIONAL | API (FastAPI) | Private | S3 / MinIO Secret Access Key. |
| `MINIO_BUCKET_NAME` | OPTIONAL | API (FastAPI) | Private | S3 Bucket name (default: `interviewos-assets`). Bucket permissions must remain strictly private. |
| `MINIO_USE_SSL` | OPTIONAL | API (FastAPI) | Private | Boolean indicating whether to connect over HTTPS (set to `True` for cloud S3/R2). |
| `SMTP_HOST` | OPTIONAL | API (FastAPI) | Private | Production SMTP relay hostname (e.g., `smtp.resend.com`, `smtp.sendgrid.net`). |
| `SMTP_PORT` | OPTIONAL | API (FastAPI) | Private | Production SMTP relay port (`587` for STARTTLS, `465` for SSL). |
| `SMTP_USER` | OPTIONAL | API (FastAPI) | Private | SMTP authentication username. |
| `SMTP_PASSWORD` | OPTIONAL | API (FastAPI) | Private | SMTP authentication password / API token. |
| `SMTP_TLS` | OPTIONAL | API (FastAPI) | Private | Enforce TLS during SMTP handshake (default: `True`). |
| `EMAIL_FROM` | OPTIONAL | API (FastAPI) | Private | Canonical sender email address (`notifications@interviewos.com`). |
| `EMAIL_FROM_NAME` | OPTIONAL | API (FastAPI) | Private | Sender display name (`InterviewOS`). |
| `STUN_SERVER_URL` | OPTIONAL | API (FastAPI) | Private | Backend STUN configuration provided dynamically in join payloads (`stun:stun.l.google.com:19302`). |
| `TURN_SERVER_URL` | OPTIONAL | API (FastAPI) | Private | Backend TURN server URL provided dynamically in join payloads. |
| `TURN_USERNAME` | OPTIONAL | API (FastAPI) | Private | Backend TURN server username. |
| `TURN_CREDENTIAL` | OPTIONAL | API (FastAPI) | Private | Backend TURN server secret credential. |
| `PORT` | **YES** | Realtime | Private | Port for the standalone Socket.IO server (default: `4000` or host `$PORT`). |
| `JWT_SECRET_KEY` | **YES** | Realtime | Private | Must match API `SECRET_KEY` to authenticate candidate and interviewer WebSocket handshakes. |
| `CORS_ORIGINS` | **YES** | Realtime | Private | Comma-separated list of origins permitted to establish WebSocket connections. |
| `CODE_RUNNER_TIMEOUT_SECONDS` | OPTIONAL | Code Runner | Private | Sandbox execution hard ceiling (default: `5.0`). |
| `CODE_RUNNER_MEMORY_LIMIT_MB` | OPTIONAL | Code Runner | Private | Container RAM limit (default: `256`). |
| `CODE_RUNNER_CPU_LIMIT` | OPTIONAL | Code Runner | Private | Container CPU quota (default: `1.0`). |
| `CODE_RUNNER_DOCKER_NETWORK` | OPTIONAL | Code Runner | Private | Isolated Docker network (default: `none` to completely block candidate outbound egress). |

---

## 2. Classification Breakdown

### A. Strictly Required for Core Vercel + Neon Operation
- `DATABASE_URL` (Neon PostgreSQL with PgBouncer connection pooling)
- `SECRET_KEY` (JWT signing and Argon2id passwords)
- `NEXT_PUBLIC_APP_URL` (Frontend URL)
- `NEXT_PUBLIC_API_URL` (Frontend API URL)
- `GROQ_API_KEY` (AI intelligence, question generation, and Whisper STT)
- `REDIS_URL` (Distributed rate limiting and state synchronization)
- `BACKEND_CORS_ORIGINS` (Cross-origin security)

### B. Required for Multi-Modal Live Interview Experience
- `NEXT_PUBLIC_REALTIME_URL` / `REALTIME_URL` (Socket.IO Realtime Gateway)
- `NEXT_PUBLIC_STUN_URL` (WebRTC camera/microphone ICE gathering)
- `JWT_SECRET_KEY` (Realtime authentication handshake)

### C. Optional with Graceful Degradation
- **S3 / Cloudflare R2 (`MINIO_*`)**: When unconfigured, the system safely falls back to local disk storage (`storage_scratch/`).
- **SMTP (`SMTP_*`)**: When unconfigured, invitation links are logged to server logs without failing API transactions.
- **TURN Relay (`TURN_*`)**: STUN handles standard NAT traversal; TURN is only activated when symmetrical firewalls block direct P2P media.
- **Docker Sandbox (`CODE_RUNNER_*`)**: Code runner falls back gracefully or uses local worker when container infrastructure is not reachable.

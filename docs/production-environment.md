# InterviewOS — Production Environment Configuration (Phase 16.2)

## 1. Environment Classification Matrix

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        INTERVIEWOS ENVIRONMENTS                        │
├───────────────────────┬────────────────────────┬───────────────────────┤
│      Development      │     Vercel Preview     │      Production       │
├───────────────────────┼────────────────────────┼───────────────────────┤
│ Local Docker / Native │ Ephemeral PR Branches  │ Live Production Tier  │
│ localhost:3000 / 8000 │ *.vercel.app Domains   │ interviewos.com       │
│ SQLite / Local PG     │ Neon Branch DB         │ Neon Main DB          │
│ Local Redis / MinIO   │ Upstash Redis / R2     │ Upstash Redis / R2    │
│ Mailpit Dev SMTP      │ Resend Sandbox         │ Resend Production     │
│ Mock/Ollama AI        │ Groq Cloud AI          │ Groq Cloud AI         │
└───────────────────────┴────────────────────────┴───────────────────────┘
```

---

## 2. Public vs Server-Only Secret Separation

> [!IMPORTANT]
> Never prepend `NEXT_PUBLIC_` to any backend secret, database password, JWT key, S3 secret key, or AI provider token. Only public URLs and non-sensitive identifiers may be prefixed with `NEXT_PUBLIC_`.

### Public Variables (Safe for Browser Bundle)
* `NEXT_PUBLIC_APP_URL` — Full URL of the frontend application (e.g. `https://interviewos.vercel.app`).
* `NEXT_PUBLIC_API_URL` — Endpoint for the HTTP API (e.g. `https://api.interviewos.com/api/v1`).
* `NEXT_PUBLIC_REALTIME_URL` — WebSocket connection URL for Socket.IO gateway (e.g. `https://realtime.interviewos.com`).
* `NEXT_PUBLIC_STUN_URL` — Public STUN server for ICE candidate discovery (e.g. `stun:stun.l.google.com:19302`).
* `NEXT_PUBLIC_TURN_URL` — (Optional) Public TURN relay URL.

### Server-Only Secrets (Backend Runtime Only)
* `DATABASE_URL` — Neon PostgreSQL pooled connection string.
* `SECRET_KEY` — Minimum 32-character high-entropy secret for Argon2id and JWT generation.
* `REDIS_URL` — TLS connection string for Upstash or Managed Redis.
* `GROQ_API_KEY` — Private API key for Groq Cloud LLM inference.
* `MINIO_SECRET_KEY` / `S3_SECRET_KEY` — Object storage secret key.
* `SMTP_PASSWORD` — SMTP relay authentication password.
* `TURN_CREDENTIAL` — TURN server secret password.

---

## 3. Production Environment Checklist

- [x] High-entropy `SECRET_KEY` generated via `openssl rand -hex 32`.
- [x] `DEBUG=False` set on all production API instances.
- [x] CORS configured strictly to `https://interviewos.vercel.app` (no wildcard `*` with credentials).
- [x] Database connection using pooled Neon endpoint with SSL (`ssl=require`).
- [x] S3 bucket permissions set to private; presigned download URLs enabled.
- [x] Zero backend credentials or private tokens exposed in client code.

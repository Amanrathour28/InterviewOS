# InterviewOS — Master Production Deployment Guide (Phase 16.2)

## Overview
This guide provides complete, step-by-step instructions for deploying **InterviewOS — AI-Native Technical Interview Platform** to production using **Vercel** (Frontend & Serverless API), **Neon PostgreSQL + pgvector** (Database), and external managed/container services for persistent realtime and code execution workloads.

---

## 1. Architecture Summary

```text
                                 INTERNET
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
               ┌──────────────────┐  ┌──────────────────┐
               │  Vercel Frontend │  │ Realtime Gateway │
               │     Next.js 14   │  │ Node.js / WSS    │
               └─────────┬────────┘  └────────┬─────────┘
                         │ HTTPS              │ WSS
                         ▼                    ▼
               ┌──────────────────┐  ┌──────────────────┐
               │    FastAPI API   │◄─┤ Redis Pub/Sub    │
               │   (Vercel/Cloud) │  │ (Upstash / Cloud)│
               └─────────┬────────┘  └──────────────────┘
                         │
        ┌────────────────┼────────────────┬────────────────┐
        ▼                ▼                ▼                ▼
 ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
 │ Neon Postgres│ │  Groq Cloud  │ │ Cloudflare R2│ │ Resend SMTP  │
 │  + pgvector  │ │  (Llama 3.3) │ │ (S3 Resumes) │ │ (Email Auth) │
 └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 2. Step-by-Step Production Deployment

### Step 1: Create Neon PostgreSQL Database
1. Go to [https://console.neon.tech](https://console.neon.tech) and create a new project named `interviewos-production`.
2. Neon automatically runs PostgreSQL 16.
3. Copy the pooled connection string:
   ```text
   postgresql://[user]:[password]@[ep-xyz-pooler].us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. In the Neon SQL Console, run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Step 2: Apply Database Migrations (001 → 016)
On your deployment workstation or CI/CD runner:
```bash
# Set your Neon connection string
export DATABASE_URL="postgresql+asyncpg://[user]:[password]@[ep-xyz-pooler].us-east-2.aws.neon.tech/neondb?ssl=require"

# Run Alembic migrations up to head (Phase 16 analytics index)
python scripts/migrate_database.py

# Run database verification check
python scripts/verify_db_connection.py
```

### Step 3: Set Up Managed Redis (Upstash / Redis Cloud)
1. Create a free database at [https://console.upstash.com](https://console.upstash.com).
2. Copy the TLS connection URL: `rediss://default:[password]@[host]:6379`.
3. Set `REDIS_URL` in your API and Realtime environments.

### Step 4: Configure Object Storage (Cloudflare R2 / AWS S3)
1. Create an S3-compatible private bucket named `interviewos-assets`.
2. Generate Access Key ID and Secret Access Key.
3. Set `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, and `MINIO_USE_SSL=True`.

### Step 5: Obtain Groq API Key
1. Register for a free API key at [https://console.groq.com](https://console.groq.com).
2. Set `GROQ_API_KEY=gsk_...` in your backend environment.

### Step 6: Deploy Frontend & API to Vercel
1. Import the `InterviewOS` repository on Vercel ([https://vercel.com/new](https://vercel.com/new)).
2. Configure **Root Directory**: `apps/web` (or root with `vercel.json`).
3. Set Environment Variables in the Vercel Dashboard:
   - `NEXT_PUBLIC_APP_URL`: `https://your-domain.vercel.app`
   - `NEXT_PUBLIC_API_URL`: `https://api.your-domain.com/api/v1` (or your FastAPI API host)
   - `NEXT_PUBLIC_REALTIME_URL`: `https://realtime.your-domain.com`
   - `NEXT_PUBLIC_STUN_URL`: `stun:stun.l.google.com:19302`
4. Click **Deploy**.

### Step 7: Deploy Persistent Realtime Service (`apps/realtime`)
1. Deploy `apps/realtime` to a container host supporting persistent WebSockets (e.g. Render, Railway, Fly.io, or VPS).
2. Configure environment:
   - `PORT`: `4000`
   - `REDIS_URL`: `rediss://...`
   - `JWT_SECRET_KEY`: Same 32-character secret as API backend.
   - `CORS_ORIGINS`: `https://your-domain.vercel.app`

### Step 8: Deploy Isolated Code Runner (`apps/code-runner`)
1. Deploy `apps/code-runner` to a dedicated VM with Docker daemon access.
2. Celery tasks consume from Redis and execute untrusted candidate code with strict limits (`network=none`, 256MB RAM, 1 CPU, 5s timeout).

---

## 3. Post-Deployment Verification
1. Access `https://your-domain.vercel.app/` and register a new company workspace.
2. Verify candidate creation, resume parsing, and interview room generation.
3. Verify live WebRTC video, Monaco collaborative code editor, and AI copilot evaluation.

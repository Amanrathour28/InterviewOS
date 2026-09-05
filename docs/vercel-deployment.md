# InterviewOS — Vercel Deployment Guide (Production)

## 1. Vercel Unified Full-Stack Architecture

InterviewOS is configured to deploy both the **Next.js 14 Web Frontend** and the **FastAPI Python Serverless API** within a single, unified Vercel project:

```text
               CLIENT BROWSER
                     │
                     ▼
          https://interviewos.vercel.app
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   /* (Web Routes)          /api/v1/* (API Routes)
        │                         │
Next.js 14 App Router     api/index.py (ASGI Adapter)
  (Edge / Node SSR)       Python 3.10+ Serverless Lambda
                                  │
                                  ▼
                         Neon PostgreSQL + pgvector
```

---

## 2. Vercel Project Configuration (Exact Settings)

In the Vercel Dashboard:
1. Click **Add New... → Project**.
2. Select **Import** next to `Amanrathour28/InterviewOS`.
3. In **Configure Project**:
   - **Project Name**: `interviewos` (or your choice)
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `./` (Leave as Root — **Do NOT change to `apps/web`** so Vercel builds both Next.js and the Python `api/index.py` Serverless function)
   - **Build Command**: *Leave blank* (Vercel automatically detects `vercel.json`: `cd apps/web && npm run build`)
   - **Output Directory**: *Leave blank* (Vercel automatically detects `vercel.json`: `apps/web/.next`)
   - **Install Command**: *Leave blank* (Vercel automatically detects `vercel.json`: `cd apps/web && npm install`)

---

## 3. Environment Variables Configuration in Vercel UI

Navigate to **Project Settings → Environment Variables** and add:

### A. Public Variables (Select: Production, Preview, Development)
| Variable | Value (Example) | Notes |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_APP_URL` | `https://interviewos.vercel.app` | Canonical public URL |
| `NEXT_PUBLIC_API_URL` | `/api/v1` | Same-domain API proxy via `vercel.json` |
| `NEXT_PUBLIC_REALTIME_URL` | `https://realtime.interviewos.com` | Persistent external Socket.IO endpoint |
| `NEXT_PUBLIC_STUN_URL` | `stun:stun.l.google.com:19302` | Google public STUN server |
| `NEXT_PUBLIC_TURN_URL` | *(Optional)* | coturn / Twilio TURN URL |
| `NEXT_PUBLIC_TURN_USERNAME` | *(Optional)* | TURN username |
| `NEXT_PUBLIC_TURN_CREDENTIAL` | *(Optional)* | TURN credential |

### B. Server-Only Secrets (Select: Production, Preview, Development)
> [!CAUTION]
> NEVER check "Automatically expose to the browser" for these secrets.

| Variable | Value | Notes |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Set to `production` |
| `DEBUG` | `False` | Disables debug stack traces |
| `SECRET_KEY` | *(Generated 32+ hex chars)* | `openssl rand -hex 32` |
| `DATABASE_URL` | `postgresql+asyncpg://...neon.tech/neondb?ssl=require` | Neon pooled connection string |
| `REDIS_URL` | `rediss://...` | TLS Redis URL (Upstash / Managed Redis) |
| `GROQ_API_KEY` | `gsk_...` | Groq Cloud API Key |
| `REALTIME_URL` | `https://realtime.interviewos.com` | Passed to clients upon joining an interview |
| `BACKEND_CORS_ORIGINS` | `["https://interviewos.vercel.app"]` | Allowed frontend domains |
| `MINIO_ENDPOINT` | *(Optional S3 endpoint)* | E.g. `s3.us-east-1.amazonaws.com` |
| `MINIO_ACCESS_KEY` | *(Optional S3 access key)* | Resumes / artifacts |
| `MINIO_SECRET_KEY` | *(Optional S3 secret key)* | Private storage |
| `MINIO_BUCKET_NAME` | `interviewos-assets` | Private S3 bucket name |
| `MINIO_USE_SSL` | `True` | HTTPS S3 connection |
| `SMTP_HOST` | *(Optional SMTP host)* | E.g. `smtp.resend.com` |
| `SMTP_PORT` | `587` | STARTTLS port |
| `SMTP_USER` | *(Optional SMTP user)* | SMTP relay user |
| `SMTP_PASSWORD` | *(Optional SMTP password)*| SMTP API key |

---

## 4. Verifying the Deployment

### Step 1: Health Check
Verify that the FastAPI serverless function and database connection are healthy:
```bash
curl -i https://<your-vercel-domain>.vercel.app/api/v1/health
```
Expected output:
```json
{"status":"healthy","database":"connected","version":"0.1.0"}
```

### Step 2: Critical Web Routes Check
Verify that all 12 platform routes return HTTP 200:
- `/` — Landing Page
- `/login` — Authentication
- `/signup` — Registration
- `/dashboard` — Recruiter / Interviewer Control Center
- `/jobs` — Job Requisitions & Competency Blueprints
- `/candidates` — Candidate Pipeline & Match Radar
- `/interviews` — Interview Schedule & Overview
- `/interviews/[id]/prepare` — Preflight Diagnostics
- `/interviews/[id]/waiting` — Candidate Waiting Room
- `/interviews/[id]/room` — Multi-Modal Collaborative Room
- `/interviews/[id]/complete` — Debrief & Evidence Summary
- `/analytics` — Executive Intelligence & Calibration Telemetry

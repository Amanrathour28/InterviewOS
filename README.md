# InterviewOS — AI-Native Technical Interview Platform

> **"Where Technical Interviews Become Intelligent."**

InterviewOS is an enterprise-grade, multi-modal technical interview platform combining HD WebRTC video, collaborative Monaco code editing with isolated Docker execution, interactive system design whiteboards, discreet real-time AI copilot assistance, evidence-grounded candidate evaluations, and executive intelligence analytics.

---

## ⚡ Platform Capabilities

- **Unified Multi-Modal Room**: Seamlessly switch between Monaco code editor, interactive system design whiteboard (tldraw), and peer-to-peer WebRTC video.
- **Sandboxed Code Execution**: Untrusted candidate code executes in strictly isolated Docker containers (`network=none`, 256MB RAM cap, 64 PIDs, 1 CPU, 5s timeout).
- **Private AI Copilot**: Real-time interviewer telemetry surfacing adaptive probing questions, code complexity insights, and rubric alignment without candidate visibility.
- **Evidence-Grounded Evaluations**: Multi-agent evaluation engine generates objective competency scores with direct citations to transcript timestamps and code snapshots.
- **Decision Intelligence & Calibration**: Executive dashboards analyzing interviewer consistency, question discrimination power, and rubric pass rates.
- **Production Cloud Architecture**: Native deployment on **Vercel** (Next.js 14 Web & Serverless API) and **Neon PostgreSQL** (PostgreSQL 16 with `pgvector`).

---

## 📂 Monorepo Structure

```text
interviewos/
├── apps/
│   ├── web/            # Next.js 14 App Router, Monaco, Zustand, Tailwind CSS (Vercel)
│   ├── api/            # FastAPI async backend, SQLAlchemy 2.0, Pydantic v2 (Vercel/Cloud)
│   ├── ai/             # Multi-agent evaluation and explanation service (Groq Cloud LLM)
│   ├── realtime/       # Node.js & Socket.IO WebRTC signaling gateway (Persistent Container)
│   └── code-runner/    # Ephemeral sandboxed Docker execution worker (Isolated VM)
├── packages/
│   └── types/          # Shared TypeScript contracts and interfaces
├── scripts/
│   ├── verify_db_connection.py  # Neon PostgreSQL and pgvector verification
│   └── migrate_database.py      # Automated Alembic migration runner
├── docs/               # Architecture, Vercel, Neon, and Phase 1-16.2 audit docs
├── vercel.json         # Vercel monorepo deployment configuration
├── docker-compose.yml  # Local development infrastructure orchestrator
└── .env.example        # Environment variable matrix template
```

---

## 🚀 Production Deployment (Vercel + Neon)

### 1. Database Setup (Neon PostgreSQL + pgvector)
1. Create a project on [Neon](https://neon.tech) and copy the pooled connection string.
2. In the Neon SQL Editor, enable pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Run migrations (`001` → `016`):
   ```bash
   export DATABASE_URL="postgresql+asyncpg://[user]:[password]@[neon-host]/neondb?ssl=require"
   python scripts/migrate_database.py
   python scripts/verify_db_connection.py
   ```

### 2. Frontend Deployment (Vercel)
1. Import repository to [Vercel](https://vercel.com/new).
2. Set **Root Directory** to `apps/web`.
3. Configure environment variables:
   - `NEXT_PUBLIC_APP_URL`: `https://your-domain.vercel.app`
   - `NEXT_PUBLIC_API_URL`: `https://api.your-domain.com/api/v1`
   - `NEXT_PUBLIC_REALTIME_URL`: `https://realtime.your-domain.com`
   - `NEXT_PUBLIC_STUN_URL`: `stun:stun.l.google.com:19302`
4. Click **Deploy**.

### 3. Persistent Services Deployment
- **Realtime Gateway (`apps/realtime`)**: Deploy to Render / Railway / Fly.io with `PORT=4000`, `REDIS_URL`, `JWT_SECRET_KEY`.
- **Code Execution Sandbox (`apps/code-runner`)**: Deploy to a dedicated Linux host with Docker daemon privileges.

---

## 💻 Local Development Setup

### 1. Launch Local Infrastructure
```bash
cp .env.example .env
docker compose up -d postgres redis minio mailpit
```

### 2. Run Database Migrations
```bash
cd apps/api
pip install -r requirements.txt
python -m alembic upgrade head
```

### 3. Launch Backend API
```bash
uvicorn app.main:app --reload --port 8000
```
API Documentation: `http://localhost:8000/api/v1/docs`

### 4. Launch Realtime Gateway
```bash
cd apps/realtime
npm install
npm run dev
```

### 5. Launch Next.js Web App
```bash
cd apps/web
npm install
npm run dev
```
Web Application: `http://localhost:3000`

---

## 📖 Comprehensive Documentation Suite

- [Production Architecture & Hosting Matrix](docs/production-architecture.md)
- [Master Production Deployment Guide](docs/deployment.md)
- [Vercel Deployment Guide](docs/vercel-deployment.md)
- [Neon PostgreSQL & pgvector Guide](docs/neon-database.md)
- [Production Environment Variables Reference](docs/production-environment.md)
- [46-Step End-to-End & Security Verification](docs/production-e2e.md)
- [Deployment Audit & Service Classification](docs/deployment-audit.md)
- [Phase 16.2 Final Report](docs/phase-16.2-final-report.md)

---

## 🔒 Security & Privacy Invariants

- **Multi-Tenant Isolation**: Strict workspace boundary verification on every database query and event channel.
- **Zero Client Secret Exposure**: Server credentials (JWT secret, DB URL, S3 secret, Groq key) never exposed to browser.
- **Untrusted Code Sandboxing**: Candidate code runs in non-networked Linux cgroup containers.
- **Cryptographic Immutability**: Finalized evaluation reports locked with SHA-256 audit trails against tampering.

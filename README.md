# InterviewOS

> **Production-Level AI Interview & Collaborative Coding Platform**

InterviewOS is an AI-native technical interview workspace combining real-time video, collaborative Monaco code editing, system design whiteboarding, isolated Docker code execution, private AI interviewer copilot telemetry, and evidence-based candidate evaluations.

---

## ⚡ Key Highlights

- **Zero-Cost Technology Stack**: Uses PostgreSQL + pgvector, Redis, MinIO, Mailpit, Monaco Editor, Yjs, tldraw, and Groq API (with Ollama local fallback).
- **Secure Code Execution**: Candidate code executes in isolated Docker sandbox workers with CPU/memory limits, execution timeouts, and zero network access.
- **Private AI Copilot**: Discreet interviewer sidebar surfaces follow-up questions, complexity evaluations, and uncovered skill telemetry without candidate visibility.
- **Unified Workspace**: Seamlessly switch between collaborative coding, whiteboard architecture, and HD WebRTC video.
- **Evidence-Based Reporting**: Generates objective candidate evaluations with transcript citations, code snapshots, and test execution metrics.

---

## 📂 Monorepo Structure

```
interviewos/
├── apps/
│   ├── api/            # FastAPI async backend (Python 3.10+, SQLAlchemy 2.0)
│   ├── web/            # Next.js 14 frontend (TypeScript, Tailwind CSS, Lucide)
│   ├── realtime/       # WebRTC signaling and WebSocket gateway
│   └── code-runner/    # Ephemeral sandboxed Docker code execution
├── packages/
│   └── types/          # Shared domain types and TypeScript schemas
├── docs/               # System architecture, database, API, and security documentation
├── docker-compose.yml  # Zero-cost infrastructure (Postgres+pgvector, Redis, MinIO, Mailpit)
└── .env.example        # Environment variable template
```

---

## 🚀 Quickstart

### 1. Configure Environment
```bash
cp .env.example .env
```

### 2. Launch Infrastructure
```bash
docker compose up -d postgres redis minio mailpit
```

### 3. Launch Backend
```bash
cd apps/api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at: `http://localhost:8000/api/v1/docs`

### 4. Launch Frontend
```bash
cd apps/web
npm install
npm run dev
```
Web Application will be available at: `http://localhost:3000`

---

## 📖 Documentation

- [Architecture Overview](docs/architecture.md)
- [Local Development Setup](docs/setup.md)
- [Database Schema & Models](docs/database.md)
- [API Conventions](docs/api.md)
- [Security Architecture & Isolation](docs/security.md)

# InterviewOS — Local Development Setup Guide

This guide walks you through setting up and running InterviewOS in your local development environment.

---

## 1. Prerequisites

Ensure you have the following installed:
- **Node.js**: v18.x or higher (v22+ recommended)
- **Python**: v3.10 or higher
- **Docker & Docker Compose**: v2.20+

---

## 2. Environment Configuration

Copy the example environment file into `.env`:

```bash
cp .env.example .env
```

Review the values in `.env`. The defaults are configured out-of-the-box for local Docker services.

---

## 3. Infrastructure via Docker Compose

Start the core database, cache, storage, and mail services:

```bash
docker compose up -d postgres redis minio mailpit
```

Verify services are running:
- **PostgreSQL**: `localhost:5432` (database: `interviewos_db`)
- **Redis**: `localhost:6379`
- **MinIO Console**: `http://localhost:9001` (user: `minioadmin`, pass: `minioadmin`)
- **Mailpit Web UI**: `http://localhost:8025`

---

## 4. Running the Backend (`apps/api`)

1. Navigate to the API folder:
   ```bash
   cd apps/api
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
5. Check health:
   - Interactive Swagger Docs: `http://localhost:8000/api/v1/docs`
   - Health check: `http://localhost:8000/api/v1/health`

---

## 5. Running the Frontend (`apps/web`)

1. Navigate to the web folder:
   ```bash
   cd apps/web
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Open your browser at `http://localhost:3000`.

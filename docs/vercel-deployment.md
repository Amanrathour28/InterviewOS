# InterviewOS — Vercel Deployment Guide (Phase 16.2)

## 1. Vercel Architecture Overview
InterviewOS web frontend is built on **Next.js 14 (App Router)** with React 18, Tailwind CSS, Monaco Editor, and Zustand state management. It is designed to run natively on Vercel's global edge and serverless infrastructure with zero server maintenance.

---

## 2. Vercel Project Setup

### Option A: Direct Web App Deployment (Recommended)
1. In the Vercel Dashboard, select **Add New... → Project**.
2. Connect your GitHub repository `https://github.com/Amanrathour28/InterviewOS.git`.
3. In **Project Settings**:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click *Edit* and select `apps/web`.
   - **Build Command**: `next build` (default)
   - **Output Directory**: `.next` (default)
   - **Install Command**: `npm install` (default)

### Option B: Monorepo Root Deployment
1. Use the provided root `vercel.json` file.
2. Build command executes `cd apps/web && npm run build`.

---

## 3. Required Environment Variables on Vercel

Add the following environment variables under **Project Settings → Environment Variables**:

| Variable Name | Environments | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_APP_URL` | Production, Preview | `https://interviewos.vercel.app` | Canonical public web URL |
| `NEXT_PUBLIC_API_URL` | Production, Preview | `https://api.interviewos.com/api/v1` | Backend HTTP API Gateway |
| `NEXT_PUBLIC_REALTIME_URL` | Production, Preview | `https://realtime.interviewos.com` | Persistent WebSocket Gateway |
| `NEXT_PUBLIC_STUN_URL` | Production, Preview | `stun:stun.l.google.com:19302` | WebRTC STUN NAT traversal |
| `NEXT_PUBLIC_TURN_URL` | Production | `turn:turn.interviewos.com:3478` | Optional TURN relay for symmetric NAT |
| `NEXT_PUBLIC_TURN_USERNAME` | Production | `interviewos_turn` | TURN credential |
| `NEXT_PUBLIC_TURN_CREDENTIAL` | Production | `secret_turn_pass` | TURN secret credential |

---

## 4. Frontend Route Verification Matrix

The deployed Vercel application serves the following production routes:

- `/` — Landing Page, Feature Highlights, and System Overview
- `/login` — Secure User Authentication (Email/Password + MFA)
- `/signup` — Organization & Workspace Registration
- `/dashboard` — Recruiter & Interviewer Control Center
- `/jobs` — Job Requisition Management & Intelligent Blueprints
- `/candidates` — Candidate Pipeline, Resume Scoring & Match Radar
- `/interviews` — Interview Schedule, Configuration & Live Rooms
- `/interviews/[id]/prepare` — Preflight Diagnostics & Device Check (Camera/Mic/Network)
- `/interviews/[id]/waiting` — Candidate Waiting Room & Sanitized Briefing
- `/interviews/[id]/room` — Live Multi-Modal Room (WebRTC, Monaco, Whiteboard, AI Copilot)
- `/interviews/[id]/complete` — Post-Interview Debrief & Evidence Summary
- `/analytics` — Executive Intelligence, Calibration Analytics & Bias Telemetry

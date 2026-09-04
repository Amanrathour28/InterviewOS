# InterviewOS — Neon PostgreSQL & pgvector Migration Guide (Phase 16.2)

## 1. Overview
InterviewOS uses **Neon Serverless PostgreSQL (PostgreSQL 16)** as its production relational database. Neon provides autoscaling, instant branching, connection pooling via PgBouncer, and native support for the `pgvector` extension.

---

## 2. Setting Up Neon PostgreSQL

### Step 1: Provision Neon Database
1. Register at [https://neon.tech](https://neon.tech).
2. Create a project named `interviewos-db`.
3. Choose the AWS region closest to your Vercel deployment (e.g., `us-east-2` for Vercel `cle1/iad1`).

### Step 2: Enable pgvector Extension
Open the Neon SQL Editor and execute:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify the extension:
```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

### Step 3: Configure Connection Pooling
In the Neon Console, choose the **Connection string** dropdown and select **Pooled connection**.
The connection string format:
```text
postgresql://[user]:[password]@[ep-xyz-pooler].[region].aws.neon.tech/neondb?sslmode=require
```

---

## 3. Database Migration Procedure (001 → 016)

The migration chain is continuous and preserved across all 16 platform phases:

| Version | Migration Name | Key Tables Created |
| :--- | :--- | :--- |
| `001` | `001_initial_auth_and_organizations` | `users`, `workspaces`, `workspace_memberships`, `audit_logs` |
| `002` | `002_jobs_and_candidates` | `jobs`, `candidates`, `candidate_applications` |
| `003` | `003_interview_configuration` | `interview_templates`, `interview_plans`, `scoring_rubrics` |
| `004` | `004_scheduling_and_calendar` | `interviews`, `interview_participants`, `invitations` |
| `005` | `005_interview_sessions_and_events` | `interview_sessions`, `interview_events` |
| `006` | `006_chat_tables` | `chat_channels`, `chat_messages` |
| `007` | `007_coding_tables` | `coding_sessions`, `code_snapshots`, `code_executions` |
| `008` | `008_problem_library_and_assessments` | `coding_problems`, `test_cases`, `starter_templates` |
| `009` | `009_whiteboard_tables` | `whiteboard_sessions`, `whiteboard_snapshots` |
| `010` | `010_interviewer_notes` | `interviewer_notes` (Private & Shared) |
| `011` | `011_ai_request_log` | `ai_request_logs` |
| `012` | `012_phase_13_intelligence_and_planning` | `resume_versions`, `job_competencies`, `candidate_job_matches` |
| `013` | `013_phase_14_adaptive_interviewer` | `adaptive_question_turns`, `transcript_segments` |
| `014` | `014_phase_15_evaluation_and_reporting` | `evaluation_reports`, `competency_scores`, `evidence_items` |
| `015` | `015_phase_15_1_evaluation_integrity` | `evaluation_audit_trail`, `tamper_detection_hashes` |
| `016` | `016_phase_16_analytics_indexes` | High-performance composite indexes for real-time analytics aggregation |

### Running Migrations:
```bash
python scripts/migrate_database.py
```

### Verifying Migrations:
```bash
python scripts/verify_db_connection.py
```

---

## 4. Connection Resilience & Serverless Adaptation
- **Async Driver**: Utilizes `asyncpg` with automatic `postgresql+asyncpg://` scheme normalization.
- **Pre-pinging**: `pool_pre_ping=True` prevents executing queries against stale or suspended Neon connections.
- **Connection Recycling**: `pool_recycle=300` automatically recycles connections every 5 minutes.
- **SSL Support**: Secure SSL connection enforced across all cloud transactions (`ssl=require`).

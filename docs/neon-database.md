# InterviewOS — Neon PostgreSQL & pgvector Migration Guide (Phase 16.2)

## 1. Overview
InterviewOS uses **Neon Serverless PostgreSQL (PostgreSQL 16)** as its production relational database. Neon provides autoscaling, instant branching, connection pooling via PgBouncer, and native support for the `pgvector` extension.

---

## 2. Setting Up Neon PostgreSQL

### Step 1: Provision Neon Database
1. Register/Login at [https://neon.tech](https://neon.tech).
2. Create a project named `interviewos-db`.
3. Choose the AWS region closest to your Vercel deployment (e.g., `us-east-2` for Vercel `iad1/cle1`).

### Step 2: Enable pgvector Extension
Open the Neon SQL Editor and execute:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify the extension:
```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

### Step 3: Obtain Connection String (Pooled)
In the Neon Console:
1. In the **Connection Details** card, ensure **Pooled connection** checkbox is checked (uses port `5432` with PgBouncer).
2. Copy the connection string. It will look like:
```text
postgresql://[user]:[password]@[ep-xyz-pooler].[region].aws.neon.tech/neondb?sslmode=require
```

---

## 3. Database Migration Procedure (001 → 016)

The migration chain is continuous and preserved across all platform phases:

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

### Executing Migrations Against Neon

Set your Neon connection string in your environment and run the migration script:

#### Windows (PowerShell):
```powershell
$env:DATABASE_URL="postgresql+asyncpg://[user]:[password]@[ep-xyz-pooler].[region].aws.neon.tech/neondb?ssl=require"
python scripts/migrate_database.py
```

#### Linux / macOS (Bash):
```bash
export DATABASE_URL="postgresql+asyncpg://[user]:[password]@[ep-xyz-pooler].[region].aws.neon.tech/neondb?ssl=require"
python scripts/migrate_database.py
```

Expected result:
```text
[InterviewOS] Starting Production Alembic Migrations...
  [PASS] Alembic migrations applied successfully.
```

### Verifying Database Integrity & pgvector

Run the verification script:
```bash
python scripts/verify_db_connection.py
```

Expected output:
```text
[InterviewOS] Starting Database Verification against: postgresql+asyncpg://***:***@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?ssl=require
  [PASS] Connection established. PostgreSQL Version: PostgreSQL 16.x ...
  [PASS] pgvector extension verified (version: 0.7.x)
  [PASS] Alembic migration head verified: 016
  [PASS] All 8 critical platform tables exist and verified.
[InterviewOS] Database verification completed successfully.
```

---

## 4. Connection Resilience & Serverless Adaptation
- **Async Driver**: Utilizes `asyncpg` with automatic `postgresql+asyncpg://` scheme normalization.
- **Pre-pinging**: `pool_pre_ping=True` prevents executing queries against stale or auto-suspended Neon connections.
- **Connection Recycling**: `pool_recycle=300` automatically recycles connections every 5 minutes.
- **SSL Support**: Secure SSL connection enforced across all cloud transactions (`ssl=require`).

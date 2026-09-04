# InterviewOS — Database Schema & Data Models

InterviewOS uses **PostgreSQL 16** with the **pgvector** extension for semantic search and async SQLAlchemy 2.0 with the `asyncpg` driver.

---

## 1. Entity Relationship Model (Phase 1 Implemented)

```
                       +-------------------+
                       |       users       |
                       +-------------------+
                       | id (UUID)         |
                       | email (unique)    |
                       | password_hash     |
                       | first_name        |
                       | last_name         |
                       | display_name      |
                       | role (enum)       |
                       | is_active         |
                       +-------------------+
                           |           |
             +-------------+           +-------------+
             |                                       |
             v                                       v
+---------------------------+             +---------------------------+
| organization_memberships  |             |     refresh_sessions      |
+---------------------------+             +---------------------------+
| id (UUID)                 |             | id (UUID)                 |
| organization_id (FK)      |             | user_id (FK)              |
| user_id (FK)              |             | token_hash (SHA-256)      |
| role (owner/admin/member) |             | expires_at                |
+---------------------------+             | is_revoked (boolean)      |
             |                            +---------------------------+
             v
+---------------------------+
|       organizations       |
+---------------------------+
| id (UUID)                 |
| name                      |
| slug (unique)             |
| created_by (FK)           |
+---------------------------+
             |
             +-------------------------------+
             |                               |
             v                               v
+---------------------------+   +---------------------------+
|        workspaces         |   |   workspace_memberships   |
+---------------------------+   +---------------------------+
| id (UUID)                 |   | id (UUID)                 |
| organization_id (FK)      |   | workspace_id (FK)         |
| name                      |   | user_id (FK)              |
| slug                      |   | role (admin/interviewer/  |
| created_by (FK)           |   |       recruiter/member)   |
+---------------------------+   +---------------------------+
```

---

## 2. Common Model Mixins

All database models inherit the following standard base mixins from `app.models.base`:

1. **UUIDPrimaryKeyMixin**: UUID v4 primary keys (`id`) using portable `sqlalchemy.Uuid(as_uuid=True)`.
2. **TimestampMixin**: `created_at` and `updated_at` timestamps with UTC timezone enforcement.
3. **SoftDeleteMixin**: `is_deleted` and `deleted_at` fields to preserve audit histories.

---

## 3. Implemented Database Tables

### Phase 1: Identity, Auth & RBAC
1. `users`: Core account identity with Argon2id password hash, global role, and active flags.
2. `organizations`: Customer tenant boundaries with unique slugs.
3. `organization_memberships`: M2M relation mapping users to organizations with `owner`, `admin`, or `member` roles.
4. `workspaces`: Sub-tenant team workspaces within organizations (e.g., Engineering, Mobile Core).
5. `workspace_memberships`: M2M relation mapping users to workspaces with granular team roles.
6. `refresh_sessions`: Server-side tracked refresh token hashes enabling revocable sessions and token rotation.
7. `password_reset_tokens`: 15-minute ephemeral tokens for self-service password reset.

### Phase 2: Jobs & Candidates
8. `jobs`: Workspace-owned job openings with status, department, and required skills.
9. `candidates`: Candidate profiles with contact details, status, and metadata.
10. `job_candidates`: M2M pipeline relationship linking candidates to jobs with stages (`applied`, `screening`, `interviewing`, `offered`, `hired`, `rejected`).
11. `candidate_tags`: Workspace-scoped reusable tags.
12. `candidate_tag_assignments`: M2M tag-candidate association.
13. `candidate_notes`: Timestamped recruiter and interviewer notes.
14. `candidate_documents`: Resume and document metadata stored in MinIO.
15. `candidate_activities`: Audit log of status transitions and pipeline events.

### Phase 3: Interview Configuration & Templates
16. `interviews`: Workspace-scoped interview configuration sessions with status machine (`draft`, `ready`, `scheduled`, `in_progress`, `completed`, `cancelled`).
17. `interview_rounds`: Sequence-ordered interview stages (`technical`, `coding`, `system_design`, `behavioral`, etc.) with duration boundaries.
18. `questions`: Categorized question bank with types, difficulty, evaluation criteria, hints, and expected duration.
19. `interview_round_questions`: Sequence join table linking rounds to bank questions.
20. `interview_participants`: Panel member assignments with roles (`lead_interviewer`, `interviewer`, `observer`, `recruiter`).
21. `interview_templates`: System and workspace-owned reusable hiring templates.
22. `interview_template_rounds`: Sequence stages belonging to templates.
23. `interview_template_questions`: Template question attachments.
24. `interview_schedules`: Confirmed/rescheduled interview instances with canonical UTC start/end times and IANA timezone.
25. `interview_schedule_history`: Full audit trail of rescheduled interview timestamps and reasons.
26. `user_availability`: Recurring weekly availability slots (day_of_week, start_time, end_time, timezone).
27. `availability_exceptions`: Date-specific blocks (holidays, leave, blocked hours).
28. `interview_invitations`: Secure participant invitation tokens with SHA-256 hash storage and lifecycle status.
29. `notifications`: In-app event alerts for schedules, reschedules, cancellations, and invitations.
30. `interview_sessions`: Authoritative live execution sessions with state machine (`waiting`, `active`, `paused`, `completed`), paused duration tracking, and last sequence counter.
31. `interview_events`: Durable chronological event log with monotonic sequence numbers, actor roles, and JSON payloads.

---

## 4. Database Migrations (Alembic)

Migrations are managed with Alembic under `apps/api/alembic/`.
- `001_initial_auth_and_organizations`: Phase 1 auth, users, orgs, workspaces, RBAC, sessions.
- `002_jobs_and_candidates`: Phase 2 jobs, candidates, pipeline, notes, tags, documents, activities.
- `003_interview_configuration`: Phase 3 interviews, rounds, questions, participants, templates.
- `004_scheduling_and_calendar`: Phase 4 interview schedules, schedule history, user availability, exceptions, invitations, notifications.
- `005_interview_sessions_and_events`: Phase 5 live interview sessions and authoritative event logs.




# InterviewOS — Security Architecture & Isolation

InterviewOS implements enterprise defense-in-depth principles:

---

## 1. Password Hashing (Argon2id)
- Passwords are encrypted using **Argon2id**, the modern IETF-recommended memory-hard hashing algorithm.
- Configuration:
  - Time cost: 3 iterations
  - Memory cost: 64 MB (65,536 KiB)
  - Parallelism: 4 lanes
  - Hash length: 32 bytes, Salt length: 16 bytes
- Plaintext passwords are never stored or logged.

---

## 2. Token & Session Strategy (JWT + Refresh Rotation)
- **Access Token**: Short-lived (60 minutes) signed with HMAC-SHA256 containing `sub` (user UUID), `email`, and `role`.
- **Refresh Token**: Long-lived cryptographic random string (`secrets.token_urlsafe(32)`).
- **Server-Side Session Tracking**: The backend persists a SHA-256 hash of the refresh token in the `refresh_sessions` table with client IP, User-Agent, expiration timestamp, and revocation flag.
- **Refresh Token Rotation**: Every call to `/api/v1/auth/refresh` revokes the incoming session and issues an entirely new token pair. If a revoked token is replayed, the request is immediately rejected (401).
- **Session Revocation**: Changing passwords automatically revokes all other active sessions across devices.
- **Cookie Security**: Tokens are delivered both in response JSON and via `HttpOnly`, `SameSite=Lax`, and `Secure` (production) cookies.

---

## 3. Strict Tenant Isolation
- Data access is enforced at the backend service/database query level.
- Dependencies:
  - `verify_org_access(org_id)`: Checks `OrganizationMembership` where `organization_id == org_id` and `user_id == current_user.id`.
  - `verify_workspace_access(workspace_id)`: Validates parent organization access and specific workspace membership.
  - `verify_interview_access(interview_id)`: Resolves interview, confirms soft delete flag is false, and verifies membership in the parent workspace.
  - `verify_question_access(question_id)`: Verifies workspace ownership for custom questions or allows read-only access for global system questions (`workspace_id IS NULL`).
  - `verify_template_access(template_id)`: Verifies workspace ownership for custom templates or allows read-only access for global system templates.
- **Verification**: Verified via automated pytest suites (`test_tenant_isolation.py`, `test_candidates.py`, `test_jobs.py`, `test_questions.py`, `test_templates.py`, `test_interviews.py`), confirming that cross-workspace data access, modification, or reordering is strictly blocked with `403 Forbidden`.

---

## 4. Role-Based Access Control (RBAC)
Role hierarchy:
1. `candidate`: Access limited strictly to candidate features (mock interviews, practice, and designated interview rooms). Cannot create workspaces or configure interviews.
2. `interviewer`: Workspace-level role allowing round evaluation and panel participation.
3. `recruiter`: Workspace-level role allowing job creation, candidate upload, and interview configuration.
4. `organization_admin`: Organization-level role with permission to manage workspaces, members, and organizational settings.
5. `platform_admin`: Cross-tenant administration with superuser privileges.

---

## 5. Lifecycle State Transitions & Readiness Integrity
- Interviews enforce a deterministic state machine in `apps/api/app/services/interview_service.py`:
  - `draft` -> `ready` (only if configuration passes all readiness criteria: >=1 round, candidate in workspace, `sum(rounds) <= duration`)
  - `ready` -> `scheduled` -> `in_progress` -> `completed`
  - Cancellation allowed from any non-terminal state.
  - Backwards transitions from terminal states (`completed` -> `draft`) are strictly rejected (`400 Bad Request`).
- Template Cloning Immutability: Instantiating an interview from a template creates wholly independent database records for the interview, rounds, and question links. Modifying or deleting a template never mutates or invalidates historical or scheduled interviews.

---

## 6. Scheduling, Interval Conflict & Invitation Security (Phase 4)
- **SHA-256 Invitation Hashing at Rest**: Raw invitation tokens (32-byte URL-safe cryptographic randomness) are presented to the client once at creation and never stored in plaintext. The database maintains exclusively a SHA-256 hash (`token_hash`) indexed with a unique constraint.
- **Zero Confidential Information Leakage on Public Invitation Surface**: The public invitation inspection endpoint (`/api/v1/invitations/{token}`) strips all internal interviewer rubrics, scoring guidelines, AI prompt instructions, and hidden candidate notes. It returns only high-level details necessary for candidate acceptance: title, job title, start/end timestamps, duration, and participant names.
- **Strict Interval Overlap Conflict Detection**: Scheduling logic implements standard interval conflict formulas (`existing_start < requested_end AND existing_end > requested_start`) to prevent candidate double-booking and interviewer panel double-booking, while safely permitting contiguous back-to-back sessions (`existing_end == requested_start`).
- **Canonical UTC Enforcement**: User-selected start timestamps are immediately converted and canonically persisted in UTC. The end timestamp is locked to `scheduled_start_at + interview.duration_minutes`, preventing clients from specifying malicious or arbitrary end times.
- **Audit Logging of Schedule Revisions**: All reschedule operations write immutable audit records to `interview_schedule_history` capturing `previous_start_at`, `new_start_at`, previous/new timezone, user identity, and timestamp.



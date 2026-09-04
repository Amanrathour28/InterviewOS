# InterviewOS — API Conventions & Endpoints

All endpoints follow strict REST standards under the prefix `/api/v1`.

---

## 1. Response & Error Envelopes

### Standard Headers
Every response includes:
- `X-Request-ID`: Distributed tracing identifier (UUID v4)
- `X-Process-Time`: Backend processing latency (e.g. `1.45ms`)

### Authentication Header
Protected endpoints require:
```
Authorization: Bearer <access_token>
```
Alternatively, browser clients can use HTTP-only cookies (`access_token` and `refresh_token`) set automatically on `/auth/login` and `/auth/register`.

---

## 2. Implemented Endpoints

### 2.1 System Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root API metadata and documentation links |
| `GET` | `/api/v1/health` | Comprehensive health check (FastAPI, DB, Redis) |
| `GET` | `/api/v1/docs` | OpenAPI / Swagger interactive documentation |
| `GET` | `/api/v1/redoc` | ReDoc API specifications |

### 2.2 Authentication & User Profile (`/api/v1/auth`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | No | Registers user, hashes password with Argon2id, creates refresh session |
| `POST` | `/api/v1/auth/login` | No | Authenticates credentials, returns access & refresh tokens |
| `POST` | `/api/v1/auth/refresh` | No | Rotates refresh token, invalidates previous session, returns new pair |
| `POST` | `/api/v1/auth/logout` | Yes | Revokes the current session and clears HTTP-only cookies |
| `GET` | `/api/v1/auth/me` | Yes | Returns current user profile, organization memberships, and active workspaces |
| `PATCH` | `/api/v1/auth/me` | Yes | Updates current user profile details (first/last/display name, avatar) |
| `POST` | `/api/v1/auth/change-password` | Yes | Validates current password, updates to new Argon2 hash, revokes other sessions |
| `POST` | `/api/v1/auth/forgot-password` | No | Generates a 15-minute one-time reset token (logged in dev) |
| `POST` | `/api/v1/auth/reset-password` | No | Resets password using valid reset token and invalidates active sessions |

### 2.3 Organizations & Tenants (`/api/v1/organizations`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/organizations` | Yes | Lists organizations where the current user holds membership |
| `POST` | `/api/v1/organizations` | Yes | Creates an organization, default workspace, and owner membership in a transaction |
| `GET` | `/api/v1/organizations/{org_id}` | Yes | Retrieves organization with workspaces (strictly verifies user membership) |

### 2.4 Workspaces (`/api/v1/workspaces`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/workspaces?organization_id={id}` | Yes | Lists workspaces for an organization (tenant access verified) |
| `POST` | `/api/v1/workspaces` | Yes | Creates workspace (requires Org Owner or Admin privileges) |
| `GET` | `/api/v1/workspaces/{workspace_id}` | Yes | Retrieves single workspace details (workspace membership verified) |

### 2.5 Jobs Requisitions (`/api/v1/jobs`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/jobs?workspace_id={id}` | Yes | Lists jobs for workspace with filters and pagination |
| `POST` | `/api/v1/jobs` | Yes | Creates a job requisition (Admin / Recruiter role required) |
| `GET` | `/api/v1/jobs/{id}` | Yes | Retrieves job requisition details |
| `PATCH` | `/api/v1/jobs/{id}` | Yes | Updates job status, description, or requirements |
| `DELETE` | `/api/v1/jobs/{id}` | Yes | Soft deletes a job requisition |

### 2.6 Candidates Management (`/api/v1/candidates`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/candidates?workspace_id={id}` | Yes | Lists candidates with search and pipeline status filters |
| `POST` | `/api/v1/candidates` | Yes | Creates a candidate profile |
| `GET` | `/api/v1/candidates/{id}` | Yes | Retrieves candidate details, notes, applications, timeline |
| `PATCH` | `/api/v1/candidates/{id}` | Yes | Updates candidate profile details |
| `DELETE` | `/api/v1/candidates/{id}` | Yes | Soft deletes a candidate profile |
| `POST` | `/api/v1/candidates/{id}/applications` | Yes | Assigns candidate to a job with initial stage |
| `PATCH` | `/api/v1/candidates/{id}/applications/{job_id}` | Yes | Advances candidate application stage |
| `POST` | `/api/v1/candidates/{id}/notes` | Yes | Appends interviewer/recruiter feedback note |
| `POST` | `/api/v1/candidates/{id}/documents` | Yes | Uploads candidate resume or document to MinIO |

### 2.7 Question Bank (`/api/v1/questions`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/questions?workspace_id={id}` | Yes | Lists workspace questions + global system questions with filters |
| `POST` | `/api/v1/questions` | Yes | Creates a categorized question with hints and rubrics |
| `GET` | `/api/v1/questions/{id}` | Yes | Retrieves question details |
| `PATCH` | `/api/v1/questions/{id}` | Yes | Updates question (system questions protected) |
| `DELETE` | `/api/v1/questions/{id}` | Yes | Soft deletes a question (system questions protected) |

### 2.8 Interview Templates (`/api/v1/interview-templates`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/interview-templates?workspace_id={id}` | Yes | Lists workspace and system templates |
| `POST` | `/api/v1/interview-templates` | Yes | Creates a template with pre-configured rounds |
| `GET` | `/api/v1/interview-templates/{id}` | Yes | Retrieves template with eager-loaded rounds and questions |
| `DELETE` | `/api/v1/interview-templates/{id}` | Yes | Soft deletes template (system templates protected) |

### 2.9 Interview Sessions & Rounds (`/api/v1/interviews`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/interviews?workspace_id={id}` | Yes | Lists interviews with status, type, candidate, and readiness filters |
| `POST` | `/api/v1/interviews` | Yes | Creates draft interview configuration |
| `POST` | `/api/v1/interviews/from-template/{template_id}` | Yes | Instantiates an interview from a template |
| `GET` | `/api/v1/interviews/{id}` | Yes | Full configuration with rounds, questions, participants, readiness |
| `GET` | `/api/v1/interviews/{id}/readiness` | Yes | Live checklist evaluating configuration completeness |
| `PATCH` | `/api/v1/interviews/{id}` | Yes | Updates interview; validates lifecycle state transitions |
| `DELETE` | `/api/v1/interviews/{id}` | Yes | Soft deletes interview |
| `GET` | `/api/v1/interviews/{id}/rounds` | Yes | Lists ordered rounds for an interview |
| `POST` | `/api/v1/interviews/{id}/rounds` | Yes | Appends a round with duration and sequence check |
| `PATCH` | `/api/v1/interviews/{id}/rounds/{round_id}` | Yes | Updates round configuration |
| `DELETE` | `/api/v1/interviews/{id}/rounds/{round_id}` | Yes | Deletes an interview round |
| `PATCH` | `/api/v1/interviews/{id}/rounds/reorder` | Yes | Reorders sequence numbers for rounds |
| `POST` | `/api/v1/interviews/{id}/rounds/{round_id}/questions` | Yes | Assigns question from bank to a round |
| `DELETE` | `/api/v1/interviews/{id}/rounds/{round_id}/questions/{question_id}` | Yes | Unassigns question from round |
| `GET` | `/api/v1/interviews/{id}/participants` | Yes | Lists assigned panel members |
| `POST` | `/api/v1/interviews/{id}/participants` | Yes | Assigns panel member (verifies workspace membership) |
| `DELETE` | `/api/v1/interviews/{id}/participants/{user_id}` | Yes | Removes panel member from interview |

### 2.10 Interview Scheduling (`/api/v1/interviews/{id}/schedule`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/v1/interviews/{id}/schedule` | Yes | Schedules interview; canonicalizes UTC and validates readiness/conflicts |
| `GET` | `/api/v1/interviews/{id}/schedule` | Yes | Retrieves active schedule and reschedule history |
| `PATCH` | `/api/v1/interviews/{id}/schedule` | Yes | Reschedules interview, logs change history, and sends email updates |
| `DELETE` | `/api/v1/interviews/{id}/schedule` | Yes | Cancels interview schedule and reverts interview state to ready |
| `GET` | `/api/v1/interviews/{id}/available-slots` | Yes | Calculates compatible candidate slots based on duration & commitments |

### 2.11 Availability & Exceptions (`/api/v1/availability`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/availability?workspace_id={id}` | Yes | Lists recurring weekly availability blocks |
| `POST` | `/api/v1/availability` | Yes | Creates a recurring weekly availability block |
| `PATCH` | `/api/v1/availability/{id}` | Yes | Modifies a recurring weekly availability block |
| `DELETE` | `/api/v1/availability/{id}` | Yes | Removes a recurring weekly availability block |
| `GET` | `/api/v1/availability/exceptions` | Yes | Lists availability exceptions (leave, holidays) |
| `POST` | `/api/v1/availability/exceptions` | Yes | Creates an availability exception block |

### 2.12 Interview Invitations
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/v1/interviews/{id}/invitations` | Yes | Dispatches invitation token and sends email |
| `GET` | `/api/v1/interviews/{id}/invitations` | Yes | Lists invitations sent for an interview session |
| `GET` | `/api/v1/invitations/{token}` | **No** (Public) | Securely inspects session metadata without rubric leakage |
| `POST` | `/api/v1/invitations/{token}/accept` | **No** (Public) | Accepts invitation and confirms participation |
| `POST` | `/api/v1/invitations/{token}/decline` | **No** (Public) | Declines invitation with optional reason |

### 2.13 Calendar Events (`/api/v1/calendar`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/calendar/events?workspace_id={id}` | Yes | Queries workspace events within start/end dates with metadata |

### 2.14 In-App Notifications (`/api/v1/notifications`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/notifications?unread_only={bool}` | Yes | Lists in-app notifications for authenticated user |
| `PATCH` | `/api/v1/notifications/{id}/read` | Yes | Marks single notification as read |
| `POST` | `/api/v1/notifications/read-all` | Yes | Marks all user notifications as read |

### 2.15 Live Interview Sessions (`/api/v1/sessions`)
| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/v1/interviews/{id}/session` | Yes | Retrieves existing active session or atomically creates new session |
| `GET` | `/api/v1/sessions/{id}` | Yes | Retrieves session state, server timestamps, participants, and elapsed time |
| `POST` | `/api/v1/sessions/{id}/start` | Yes (Interviewer) | Transitions session from waiting to active |
| `POST` | `/api/v1/sessions/{id}/pause` | Yes (Interviewer) | Transitions session from active to paused |
| `POST` | `/api/v1/sessions/{id}/resume` | Yes (Interviewer) | Transitions session from paused to active |
| `POST` | `/api/v1/sessions/{id}/end` | Yes (Interviewer) | Transitions session and parent interview to completed |
| `POST` | `/api/v1/sessions/{id}/stage` | Yes (Interviewer) | Transitions interview stage (`introduction`, `coding`, etc.) |
| `GET` | `/api/v1/sessions/{id}/events` | Yes | Retrieves durable event stream with `after_sequence` filtering |
| `POST` | `/api/v1/sessions/{id}/join-token` | Yes | Generates short-lived HMAC-SHA256 JWT for WebSocket handshake |




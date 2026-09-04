# Interview Control Center (Phase 11)

The **Interview Control Center** transforms InterviewOS into a cohesive, professional operating environment for technical interviewers.

---

## 1. Core Architecture

The Control Center operates on a **Server-Authoritative State Machine** governing the entire session lifecycle:
- **`WAITING`**: Initial state where interviewers and candidates can conduct device checks and network diagnostics.
- **`ACTIVE`**: Live state where timer is actively running and technical assessments are conducted.
- **`PAUSED`**: Intermediate state for bio breaks or technical difficulties. Accumulates `total_paused_seconds` server-side without advancing the timer.
- **`COMPLETED`**: Final state. Freezes all technical artifacts (Monaco files, test executions, Whiteboard snapshots) and produces the final evaluation record.

---

## 2. Key Components

### 1. Stage Stepper (`stage-stepper.tsx`)
- Standardized stages:
  1. **Introduction & Agenda**
  2. **Behavioral & Experience**
  3. **Core Technical Background**
  4. **Live Coding Assessment**
  5. **System Design Architecture**
  6. **Candidate Q&A & Closing**
- Interviewer can click any stage to transition the room state.
- Emits real-time `STAGE_CHANGED` event to all participants, prompting a stage transition banner on candidate viewports.

### 2. Synchronized Timer (`interview-timer.tsx`)
- Computed from `started_at`, `paused_at`, `total_paused_seconds`, and `duration_minutes`.
- Prevents client clock skew or tampering.
- Features prominent visual PAUSED banner and low-time warnings (< 5 minutes).

### 3. Structured Private Notes (`structured-notes-panel.tsx`)
- Private notes categorized by:
  - `Rubric Score`
  - `Coding Assessment`
  - `System Design`
  - `Behavioral & Comm`
   panel
  - `General Notes`
- Includes 1–5 star rating scale and hashtag taxonomy.
- Strictly isolated: Candidate JWT tokens are blocked with `403 Forbidden` from reading or writing notes.

### 4. Live Activity Timeline (`activity-timeline-drawer.tsx`)
- Slide-over drawer recording durable events across the interview lifecycle:
  - Stage transitions
  - Participant joins/leaves
  - Code executions and problem submissions
  - Whiteboard snapshots and lock/unlock actions
  - Chat activity
- Filterable by event category.

### 5. Deliberate End Interview Modal (`end-interview-modal.tsx`)
- Multi-point archival verification checklist ensuring all code, diagrams, and notes are preserved before concluding.

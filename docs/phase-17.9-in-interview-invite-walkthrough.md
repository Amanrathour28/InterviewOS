# Walkthrough — Phase 17.9: In-Interview Invite Link / Google Meet-Style Sharing

## Overview
We have implemented the Google Meet-style **In-Interview Candidate Invite Link and Sharing** feature for InterviewOS. Interviewers can now retrieve the candidate join link directly from within an active interview room, copy it with a single click, or share it via the Web Share API — without disrupting ongoing WebRTC video, Socket.IO connections, timers, whiteboard, or collaborative code.

---

## Key Architecture Highlights

1. **Zero Database Migrations / Schema Changes**:
   - The candidate join token is generated deterministically via HMAC-SHA256:
     ```python
     raw_token = _derive_interview_candidate_token(interview_id, settings.SECRET_KEY)
     token_hash = _sha256(raw_token)
     ```
   - Clicking "Invite" multiple times is **100% idempotent**: it always returns the exact same candidate join URL without creating redundant rows or invalidating active tokens.
   - The join URL generated inside the room matches the URL generated at interview creation:
     `https://interviewos-nine.vercel.app/join/<token>`

2. **Full Reuse of Phase 17 Candidate Flow**:
   - Candidate opens the copied link -> lands on `/join/[token]`.
   - Submits guest identity -> receives candidate session JWT.
   - Accesses `/join/[token]/room` -> connects to the same WebRTC room and Socket.IO session.
   - Works across separate browsers, devices, and incognito sessions.

3. **Security**:
   - Never exposes interviewer JWT, database credentials, or private internal notes.
   - Endpoint `/api/v1/interviews/{interview_id}/invite-link` verifies interviewer authentication and workspace ownership via `verify_interview_access`.
   - Anonymous requests are rejected with HTTP 401; unauthorized workspace users with HTTP 403/404.

---

## Changes Implemented

### 1. Backend API (`apps/api`)

- **`apps/api/app/api/v1/endpoints/instant_interview.py`**:
  - Added `_derive_interview_candidate_token(interview_id, secret_key) -> str`.
  - Added `InterviewInviteLinkResponse` schema.
  - Added `GET /api/v1/interviews/{interview_id}/invite-link` & `POST /api/v1/interviews/{interview_id}/invite-link` with `verify_interview_access`.
  - Updated `create_instant_interview` to use `_derive_interview_candidate_token` ensuring identical URLs across the platform.

- **`apps/api/tests/test_instant_interview.py`**:
  - Added regression test `test_get_interview_invite_link_success_and_idempotent`.
  - Added authorization check test `test_get_interview_invite_link_authorization_check`.

### 2. Frontend Web (`apps/web`)

- **`apps/web/components/interview-room/invite-candidate-modal.tsx`** (New):
  - Google Meet-style dialog with title *"Invite to this interview"* and subtitle *"Share this link with the candidate to join this interview."*
  - Readonly input displaying `join_url`.
  - **Copy link** button with clipboard write, fallback selection, "Copied!" button feedback, and floating toast notification.
  - **Share interview** button leveraging `navigator.share` with fallback to copy link.
  - Expiration note calculating remaining validity (e.g. *"Link expires in 48 hours"*).
  - Accessibility: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, Escape key dismissal, autofocus, backdrop dismiss.

- **`apps/web/app/(authenticated)/interviews/[interviewId]/room/page.tsx`**:
  - Added header **Invite** button with `UserPlus` icon placed prominently near the Panel button.
  - Added **Waiting for candidate** empty state card in the Live Video grid with an **Invite candidate** CTA button when alone in the room.
  - Added **Waiting for candidate** CTA in the collapsible Session Panel.
  - Added floating toast alert for copy/sharing confirmation.
  - Non-disruptive modal rendering that never resets timers or media streams.

---

## Verification Results

### Automated Tests

1. **Backend Pytest**:
   ```bash
   $env:PYTHONPATH="."; .\venv\Scripts\python -m pytest tests/test_instant_interview.py -q
   ```
   **Result**: `28 passed, 1 warning in 21.97s` (100% pass rate).

2. **Frontend Typecheck**:
   ```bash
   npx tsc --noEmit -p apps/web/tsconfig.json
   ```
   **Result**: 0 type errors.

3. **Frontend Production Build**:
   ```bash
   npm run build
   ```
   **Result**: Next.js production build compiled cleanly across all 21 static and dynamic routes.

---

## 20-Point Verification Scorecard

| Check | Requirement | Result | Evidence / Notes |
|:---|:---|:---:|:---|
| 1 | Invite button | **PASS** | Header `Button` with `UserPlus` icon placed adjacent to Panel controls |
| 2 | Invite dialog | **PASS** | `InviteCandidateModal` with *"Invite to this interview"* and *"Share this link..."* |
| 3 | Correct existing join URL | **PASS** | Resolves candidate join link from existing Phase 17 `/join/{token}` architecture |
| 4 | Copy link | **PASS** | Copies join URL, switches button to *"Copied!"*, displays toast notification |
| 5 | Browser Share API | **PASS / FALLBACK** | Uses `navigator.share` when supported; falls back cleanly to copy link |
| 6 | Separate-browser join | **PASS** | Candidate can open `/join/{token}` in another browser/incognito session |
| 7 | Candidate authentication | **PASS** | Candidate provides name/email at `/identity` and receives candidate session JWT |
| 8 | Candidate enters interview | **PASS** | Candidate retrieves `/room-session` and connects to room WebRTC & Socket.IO |
| 9 | Interviewer sees candidate | **PASS** | Candidate presence updates `Panel (2)` and Live Video remote stream |
| 10 | Existing WebRTC | **PASS** | Remote audio and video continue functioning without interruption |
| 11 | Existing chat | **PASS** | Bidirectional chat channel persists when opening/closing Invite dialog |
| 12 | Existing whiteboard | **PASS** | Tldraw collaborative state preserved; dialog does not disrupt canvas |
| 13 | Existing collaborative code | **PASS** | Monaco editor state and execution channels remain connected |
| 14 | Responsive UI | **PASS** | Tested across 1920x1080 down to mobile viewport widths |
| 15 | Accessibility | **PASS** | `aria-label="Invite people to this interview"`, Escape key dismiss, focus trap |
| 16 | Non-disruptive modal | **PASS** | Opening/closing dialog never disconnects Socket.IO, WebRTC, or timer |
| 17 | Waiting video empty state | **PASS** | Live Video area shows *"Waiting for candidate"* card with *"Invite candidate"* CTA |
| 18 | Session panel empty state | **PASS** | Participant Panel displays *"Waiting for candidate"* with *"Invite candidate"* CTA |
| 19 | Multiple invite clicks | **PASS** | Deterministic HMAC derivation guarantees 100% idempotency with zero duplicate rows |
| 20 | Security / No credential leakage | **PASS** | URL contains only URL-safe join token; never exposes interviewer JWT or DB secrets |

**Backend Model / Endpoint Reused**:
- Reused `InterviewInvitation` (`apps/api/app/models/scheduling.py`) with `RecipientType.CANDIDATE`.
- Reused public candidate join endpoints:
  - `GET /api/v1/interviews/join/{token}`
  - `POST /api/v1/interviews/join/{token}/identity`
  - `GET /api/v1/interviews/join/{token}/room-session`
- Added authenticated endpoint:
  - `GET & POST /api/v1/interviews/{interview_id}/invite-link`

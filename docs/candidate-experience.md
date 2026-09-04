# Candidate Experience & Waiting Room (Phase 11)

InterviewOS provides a focused, premium, low-stress environment for technical candidates.

---

## 1. Candidate Waiting Room (`/interviews/[interviewId]/waiting`)

Prior to joining the live interview session, candidates enter a dedicated preparation waiting room:
1. **Device Pre-checks**:
   - Live video camera preview with device switcher.
   - Microphone input level meter showing realtime audio energy percentage.
   - Speaker chime test for verifying audio output.
2. **Network Diagnostics**:
   - WebRTC ICE connection readiness check.
   - Real-time latency indicator.
3. **Format Guidelines & Instructions**:
   - Review interview format, scheduled duration, and expectations.
4. **Readiness Signal**:
   - Emits `candidate_ready` socket event when joining.

---

## 2. Live Interview Room Candidate View (`/interviews/[interviewId]/room`)

- **Focused Interface**:
  - Full access to video feeds, collaborative Monaco code editor, and System Design whiteboard.
  - No access to interviewer private controls, rubric scoring notes, or internal hidden problem test cases.
- **Stage Progression Alerts**:
  - Floating toast notifications whenever the interviewer advances the stage (e.g., *"Interview Stage Advanced to: LIVE CODING"*).
- **Synchronized Countdown**:
  - Displays remaining allocated time and pause indicators.

---

## 3. Interview Completion Page (`/interviews/[interviewId]/complete`)

- Professional completion confirmation reassuring the candidate that all code files and architecture diagrams have been recorded and saved.
- Clear instructions on next steps from the hiring organization.

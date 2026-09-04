# Coding Assessment & Test Evaluation Engine

## Overview
InterviewOS features an automated coding assessment system that evaluates candidate submissions in isolated Docker sandboxes against weighted test suites with strict confidentiality for hidden test cases.

---

## 1. Submission & Evaluation Pipeline

```
Candidate Solution Submission
               │
               ▼
  Create Immutable CodingSnapshot (reason: submission)
               │
               ▼
  Enqueue CodingExecutionJob (is_submission: True)
               │
               ▼
  DockerSandboxExecutor runs candidate code against:
   ├── Public Test Cases
   └── Confidential Hidden Test Cases
               │
               ▼
  Compute Weighted Score & Verdict
   (Accepted, Wrong Answer, TLE, Memory Limit, Compile Error)
               │
               ▼
  Persist CodingSubmission & Upsert CodingAssessment
               │
               ▼
  Emit Monotonic Realtime InterviewEvent
   (CODING_SUBMISSION_CREATED)
               │
               ▼
  Public vs. Interviewer Response Sanitization
```

---

## 2. Hidden Test Confidentiality Matrix

| Data Field | Candidate View | Interviewer View |
| :--- | :--- | :--- |
| **Public Test Input** | `[2, 7, 11, 15], 9` | `[2, 7, 11, 15], 9` |
| **Public Test Expected** | `[0, 1]` | `[0, 1]` |
| **Hidden Test Input** | `None` / Redacted ⛔ | Full Input Data ✅ |
| **Hidden Test Expected** | `None` / Redacted ⛔ | Full Expected Output ✅ |
| **Hidden Test Verdict** | Pass / Fail Status only | Full stdout/stderr & diagnostics |
| **Hidden Test Title** | Masked to "Hidden Test Case" | Original Test Title |

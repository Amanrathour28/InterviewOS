# AI Interviewer Realtime Events — Phase 14

## Channel Architecture

```
Socket.IO Gateway
  ├── interview:{sessionId}:public (Candidate + Interviewer)
  │     └── TRANSCRIPT_SEGMENT_RECEIVED
  │
  └── interview:{sessionId}:interviewer (Interviewer Only)
        ├── AI_RECOMMENDATION_CREATED
        ├── AI_RECOMMENDATION_ACCEPTED
        ├── AI_RECOMMENDATION_EDITED
        ├── AI_RECOMMENDATION_REJECTED
        ├── AI_RECOMMENDATION_SKIPPED
        ├── AI_RECOMMENDATION_STALE
        └── AI_COVERAGE_UPDATED
```

## Security Invariant

Candidate connections are blocked from joining `interview:{sessionId}:interviewer`. Any AI recommendation event is delivered strictly to authenticated interviewers.

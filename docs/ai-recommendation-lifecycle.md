# AI Recommendation Lifecycle — Phase 14

## State Transition Machine

```
   [GENERATING]
        │
        ▼
   [GENERATED]
        │
        ▼
   [VALIDATED]
        │
        ▼
   [PRESENTED]
   ┌────┴──────────────────────────┬─────────────────┐
   ▼                               ▼                 ▼
[ACCEPTED]                     [EDITED]          [REJECTED] / [SKIPPED]
   │                               │                 │
   └───────────────┬───────────────┘                 ▼
                   ▼                            [ARCHIVED]
       Recorded in Durable Log
       & Coverage Incremented

Special Transitions:
- Context Revision Advance ──► [STALE] (Cannot be accepted without regeneration)
- Interview Complete / Cancelled ──► [EXPIRED]
```

## Audit Trail Guarantees

Every transition captures:
- Timestamp (UTC)
- Reviewing User ID
- Original AI Question vs Edited Question text
- Rejection reason if declined
- Target competency evidence updates

# Live Interview Context Model — Phase 14

## Schema Structure

```
LiveInterviewContext
├── interview (id, status, current_stage, elapsed_seconds, remaining_seconds)
├── question_plan (approved_items, target_competencies, difficulty_bounds)
├── current_question (id, text, competency, difficulty, asked_at)
├── candidate_response (recent_segments, normalized_text, duration, boundary_status)
├── competency_evidence (competency, strength, questions_asked, demonstrated, missing)
├── resume_claims (claim, priority, status, evidence_source)
├── coding_state (problem_id, execution_summary, tests_passed, time_complexity)
├── system_design_state (components, tradeoffs, single_points_of_failure)
├── interviewer_context (notes, accepted_recommendations, rejected_recommendations)
└── context_revision (monotonic revision counter)
```

## Monotonic Context Revision & Stale Invalidation

Every new transcript segment or state modification increments `context_revision`.
When `context_revision` advances:
- Unreviewed active recommendations are automatically invalidated (`status = 'stale'`).
- Prevents interviewers from accidentally asking outdated probes after the discussion has moved forward.

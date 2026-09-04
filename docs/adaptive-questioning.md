# Adaptive Questioning Engine — Phase 14

## Decision Matrix & Action Set

The Adaptive Questioning Engine selects recommendations from a defined action taxonomy:

| Action | Purpose | Trigger Condition |
| :--- | :--- | :--- |
| `ASK_APPROVED_QUESTION` | Progress along Question Plan | Next scheduled competency with no active response |
| `GENERATE_FOLLOW_UP` | Deepen evidence on candidate answer | Candidate gave high-level overview without trade-offs |
| `INCREASE_DIFFICULTY` | Calibrate upper bounds of mastery | Candidate demonstrates strong proficiency on fundamentals |
| `DECREASE_DIFFICULTY` | Provide scaffolded conceptual probe | Candidate is stuck or missing key prerequisite concepts |
| `PROBE_WEAK_EVIDENCE` | Address identified technical gaps | Candidate skipped error handling or edge cases |
| `PROBE_RESUME_CLAIM` | Verify high-impact resume statement | High-priority resume claim matches current topic |
| `MOVE_TO_NEXT_COMPETENCY` | Maintain interview pacing | Competency marked as covered and remaining time is low |
| `SKIP_LOW_VALUE_QUESTION` | Optimize remaining minutes | High evidence already established on target competency |

## Anti-Duplication Protection

1. **Exact Duplicate Check**: Normalized character comparison against previously asked questions.
2. **Semantic / Lexical Overlap**: Word token set Jaccard similarity thresholded at 80%.
3. **Conceptual Duplicate Prevention**: Tracks assessed competencies and signal targets.

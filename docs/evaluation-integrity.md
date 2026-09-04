# InterviewOS Evaluation Integrity Framework

## 1. Core Philosophy & Trust Hierarchy

The fundamental principle governing InterviewOS evaluations is:
> **AI may interpret evidence, but it must never invent evidence.**
> **LLM reasoning is advisory; deterministic scoring and persisted evidence are authoritative.**

### Trust Boundary & Evaluation Hierarchy

```text
1. Persisted Multi-Modal Evidence (authoritative truth: transcripts, sandbox execution, whiteboard)
      ↓
2. Validated Evidence References (existence + tenant ownership checks)
      ↓
3. Grounded AI Claims (semantic alignment validation + quote verification)
      ↓
4. AI Competency Rubric Proposals (1.0 to 5.0 qualitative assessment)
      ↓
5. Deterministic Scoring Service (pure weighted mathematical formula 0-100)
      ↓
6. Deterministic Recommendation Engine (policy thresholds + safety gates)
      ↓
7. Human Interviewer Review & Audited Overrides (mandatory rationale logging)
      ↓
8. Finalized Immutable EvaluationVersion (cryptographic SHA-256 seal + locked state)
```

---

## 2. Invariants Enforced

1. **Zero Hallucination / Anti-Fabrication**:
   - Citations must reference actual persisted `EvaluationEvidence` UUIDs belonging to the same workspace & interview.
   - Claims are semantically validated against evidence content; unsupported claims are excluded from scoring.
   - Quotes attributed to candidates are verified against candidate speech records; fabricated quotes are rejected.

2. **Deterministic Recommendation Invariance**:
   - AI-suggested recommendations in text/synthesis payloads are ignored.
   - The final recommendation is computed exclusively from the mathematical score and safety gates (`STRONG_HIRE`, `HIRE`, `LEAN_HIRE`, `LEAN_NO_HIRE`, `NO_HIRE`, `INSUFFICIENT_EVIDENCE`).

3. **100% Score Reproducibility**:
   - Scores are computed from `EvaluationScoreInput` via deterministic algebraic formulas.
   - Independent of LLM provider, temperature, evidence ordering, or database retrieval ordering.

4. **Immutable Sealing & Cryptographic Hash**:
   - Finalized evaluations create an immutable `EvaluationVersion` with a canonical SHA-256 integrity hash.
   - All subsequent mutation attempts are rejected server-side with `HTTP 422`.

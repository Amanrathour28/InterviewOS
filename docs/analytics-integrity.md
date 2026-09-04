# Analytics Integrity, Trust Model & Metric Contracts

## 1. Analytics Trust Model

InterviewOS maintains a strict separation between deterministic data aggregation and non-authoritative advisory AI explanations:

```text
Raw Operational Data (Interviews, Transcripts, Code Runs)
        ↓
Validated Evidence & Rubrics
        ↓
Finalized Immutable Evaluations (SHA-256 Sealed)
        ↓
Deterministic Analytics Services (Python / SQLAlchemy)
        ↓
Presentation & Dashboard Metrics
        ↓
Optional Advisory AI Explanations (Grounded, Non-Authoritative)
```

### Core Invariants:
1. **AI Never Calculates Metrics**: Counts, sums, averages, medians, percentiles, and recommendation rates are calculated exclusively in deterministic Python routines.
2. **Authoritative Finalized Separation**: Finalized evaluation decisions and scores cannot be mutated by operational edits to candidate profiles or draft revisions.
3. **Domain Safety**: All candidate scores are strictly constrained to $[0.0, 100.0]$. Values outside this domain are rejected.

---

## 2. Canonical Metric Contracts Table

| Metric | Formula | Source Entities | Denominator | Minimum Sample ($n$) | Authoritative? |
|---|---|---|---|---|---|
| **Completion Rate** | $\frac{\text{Completed Interviews}}{\text{Total Scheduled/Started}} \times 100$ | `Interview`, `InterviewSession` | Total interviews in window | $n \ge 1$ | Yes |
| **Cancellation Rate** | $\frac{\text{Cancelled Interviews}}{\text{Total Scheduled/Started}} \times 100$ | `Interview` | Total interviews in window | $n \ge 1$ | Yes |
| **No-Show Rate** | $\frac{\text{Expired / No-Show Interviews}}{\text{Total Scheduled/Started}} \times 100$ | `Interview` | Total interviews in window | $n \ge 1$ | Yes |
| **Hire Rate** | $\frac{\text{Strong Hire} + \text{Hire} + \text{Lean Hire}}{\text{Total Finalized Evaluations}} \times 100$ | `Evaluation` | Finalized evaluations in window | $n \ge 1$ | Yes |
| **Average Score** | $\frac{1}{n} \sum_{i=1}^{n} \text{overall\_score}_i$ | `Evaluation` | Number of finalized evaluations | $n \ge 1$ | Yes |
| **Score Percentiles** | Deterministic Linear Interpolation ($P_{25}, P_{50}, P_{75}, P_{90}$) | `Evaluation` | Number of finalized evaluations | $n \ge 1$ | Yes |
| **Evidence Yield** | $\frac{\text{Grounded Evidence Observations}}{\text{Questions Asked}}$ | `EvaluationEvidence`, `Question` | Questions asked in window | $n \ge 3$ | Yes |
| **Calibration Signal** | $\text{Interviewer Mean Score} - \text{Workspace Baseline Mean}$ | `Evaluation`, `InterviewParticipant` | Finalized evaluations per interviewer | $n \ge 10$ | Yes (Signal) |
| **AI Advisory Explanation** | Natural language synthesis over structured metrics | Backend Analytics Output | N/A | N/A | No (Advisory) |

# Problem Versioning & Immutability Architecture

## Overview
To ensure reproducibility in technical interviewing, InterviewOS binds interview sessions to immutable problem versions rather than mutable problem rows.

---

## 1. Version Lifecycle

```
Problem Creation (v1)
      │
      ▼
Assigned to Interview Session A (bound to v1)
      │
      ▼
Interviewer updates problem statement or test cases
      │
      ▼
System generates Version 2 (v2)
      │
      ├── Past Interview Session A remains on v1 (unchanged) ✅
      └── Future Interview Session B uses v2 ✅
```

---

## 2. Version Entity Schema

`CodingProblemVersion` captures the exact assessment specification:
- `version_number`: Monotonically incrementing integer per problem.
- `problem_statement`: Markdown description.
- `examples`: Structured input, output, explanations.
- `constraints`: List of algorithmic constraints.
- `starter_codes`: Language-to-code mapping.
- `scoring_policy`: Test weighting rules.
- `test_cases`: Public and hidden test specifications.

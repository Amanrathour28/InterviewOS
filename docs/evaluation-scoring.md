# Deterministic Scoring & Recommendation Engine

## 1. Rubric Score Conversion
Competency rubric levels range from `1.0` (Unsatisfactory) to `5.0` (Exemplary).
Formula to map rubric level $L$ to score $S \in [0.0, 100.0]$:
$$S = \frac{L - 1.0}{4.0} \times 100.0$$

- $1.0 \to 0.0$
- $2.0 \to 25.0$
- $3.0 \to 50.0$
- $4.0 \to 75.0$
- $5.0 \to 100.0$

## 2. Weighted Overall Score Calculation
For assessed competencies $i=1 \dots N$ with rubric levels $L_i$ and weights $W_i$:
$$\text{Overall Score} = \frac{\sum_{i=1}^N (S_i \times W_i)}{\sum_{i=1}^N W_i}$$

## 3. Hiring Recommendation Policy Thresholds
Recommendations are derived deterministically from the overall score:

| Overall Score Range | Recommendation |
|---|---|
| $\ge 85.0$ | `STRONG_HIRE` |
| $\ge 70.0$ and $< 85.0$ | `HIRE` |
| $\ge 55.0$ and $< 70.0$ | `LEAN_HIRE` |
| $\ge 40.0$ and $< 55.0$ | `LEAN_NO_HIRE` |
| $< 40.0$ | `NO_HIRE` |

### Safety Gates:
1. **Insufficient Evidence Gate**: If assessed competencies count $< 1$, or average confidence $< 0.40$, or any required competency is not assessed, recommendation is strictly `INSUFFICIENT_EVIDENCE`.
2. **Critical Contradiction Gate**: If a critical contradiction between resume claims and observed performance exists, `STRONG_HIRE` is downgraded to `LEAN_HIRE`, and lower scores become `NO_HIRE`.

## 4. Score Reproducibility Verification
`EvaluationScoreInput` stores:
- `scoring_formula`: `"weighted_rubric_average"`
- `competency_weights`: e.g. `{"Coding": 2.0, "System Design": 1.5}`
- `competency_rubric_levels`: e.g. `{"Coding": 4.5, "System Design": 4.0}`
- `calculated_overall_score` & `calculated_recommendation`

Recalculating scores from this input yields zero variance across all executions.

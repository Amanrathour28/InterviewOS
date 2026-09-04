# Analytics Statistical Methodology & Calibration Model

## 1. Percentile Computation Methodology

InterviewOS implements deterministic linear interpolation for percentile calculation over sorted scores:

Given $n$ sorted scores $S = [s_0, s_1, \dots, s_{n-1}]$ and percentile $p \in [0, 1]$:
$$k = (n - 1) \cdot p$$
$$f = \lfloor k \rfloor, \quad c = \lceil k \rceil$$
$$\text{percentile}(p) = S[f] \cdot (c - k) + S[c] \cdot (k - f)$$

This guarantees:
- $P_{25} \le P_{50} \le P_{75} \le P_{90}$ for any dataset.
- $P_{50} = \text{median}$ for all sample sizes.
- Identical outputs across Python, database, and client implementations.

---

## 2. Interviewer Calibration Model

To prevent bias mischaracterization and respect sample sizes, interviewer scoring variance is modeled objectively as a **Calibration Signal**:

1. **Workspace Baseline ($\mu_{\text{ws}}$)**:
   $$\mu_{\text{ws}} = \frac{1}{N} \sum_{j=1}^{N} \text{score}_j \quad \text{for all finalized evaluations in window}$$

2. **Interviewer Delta ($\Delta_i$)**:
   $$\Delta_i = \bar{s}_i - \mu_{\text{ws}}$$

3. **Sample Size Gating ($n \ge 10$)**:
   - If $n < 10$: Classified as `INSUFFICIENT_SAMPLE`. No definitive variance signal is emitted.
   - If $|\Delta_i| \le 5.0$: `CALIBRATED` (within expected scoring tolerance).
   - If $\Delta_i > +5.0$: `UPWARD_VARIANCE` (scores trend higher than workspace baseline).
   - If $\Delta_i < -5.0$: `DOWNWARD_VARIANCE` (scores trend lower than workspace baseline).

---

## 3. Question Discrimination & Evidence Yield

- **Evidence Yield**: Average number of semantic evidence items produced per question utilization ($n \ge 3$).
- **Discrimination Signal**: Standard deviation of candidate scores for a specific question:
  - High discrimination: $\sigma \ge 15.0$
  - Moderate discrimination: $8.0 \le \sigma < 15.0$
  - Low discrimination: $\sigma < 8.0$

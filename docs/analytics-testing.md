# Analytics Verification & Adversarial Testing Matrix

## 1. Test Suite Organization

| Test Module | Coverage Area | Key Invariants Tested |
|---|---|---|
| `test_analytics_scoring.py` | Score & Recommendation Math | Mean, median, percentiles, distribution sum, hire rates |
| `test_analytics_filters.py` | Time Windows & Overrides | `7d` to `365d`, quarter boundaries, custom date overrides |
| `test_analytics_reproducibility.py` | Determinism & Finalized Isolation | Draft vs finalized separation, identical output across runs |
| `test_analytics_isolation.py` | Tenant Isolation & RBAC | Candidate 403 rejection, foreign workspace query rejection |
| `test_analytics_integrity.py` | Score Domain & Immutability | $[0, 100]$ score bounds, negative/NaN rejection |
| `test_analytics_metrics.py` | Denominator & Percentile Precision | Zero-sample safety, monotonic percentiles |
| `test_analytics_security.py` | 401/403 Security Boundaries | Comprehensive RBAC audit across all 12 endpoints |
| `test_analytics_tenant_isolation.py` | Drill-Down & Cache Scoping | Multi-tenant cache keys, candidate timeline isolation |
| `test_analytics_exports.py` | Export Sanitization | Token, password, private notes, hidden test stripping |
| `test_analytics_time_windows.py` | UTC & Quarter Semantics | Canonical UTC timestamps, half-open intervals |
| `test_analytics_concurrency.py` | Concurrency & Thread Safety | 20 concurrent calculations, pure function determinism |
| `test_analytics_ai_explanation.py` | AI Explanation Agent | Grounding, sanitization, prompt injection quarantine |
| `test_analytics_explanation_integrity.py` | Explanation Faithfulness | Faithful representation of input metrics, graceful fallback |
| `test_analytics_explanation_injection.py` | Prompt Injection Defense | Quarantine delimiters, rejection of override instructions |

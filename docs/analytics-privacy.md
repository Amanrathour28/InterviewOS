# Analytics Privacy, Data Minimization & Tenant Isolation

## 1. Multi-Tenant Hardening

InterviewOS enforces tenant boundaries across all analytics layers:

```text
HTTP Request
     ↓
verify_workspace_access (Verifies Org & Workspace Membership)
     ↓
require_non_candidate (Blocks CANDIDATE role with HTTP 403)
     ↓
SQL Queries (Hard-filter WHERE workspace_id = :workspace_id)
     ↓
Cache Keys (analytics:{workspace_id}:{endpoint}:{filter_hash})
     ↓
Sanitization & Privacy Minimization
```

---

## 2. PII & Secret Minimization in Exports

The `AnalyticsExportService` strictly purges internal security tokens, credentials, private interviewer comments, and unnecessary candidate PII from all CSV and JSON exports:

### Explicitly Excluded Fields:
- `password`, `hashed_password`
- `api_key`, `token`, `access_token`, `refresh_token`
- `email` (anonymized/minimized to `candidate_id` and name where authorized)
- `integrity_hash`, `snapshot_payload`
- `private_notes`
- `hidden_tests`, `hidden_test_cases`
- `system_prompt`, `chain_of_thought`, `cot`

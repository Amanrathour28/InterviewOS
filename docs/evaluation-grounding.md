# Semantic Evidence Grounding & Anti-Hallucination Framework

## 1. Grounding Model & Claim Verification
Every AI-generated claim is subject to automated grounding validation before being persisted or factored into evaluation reports.

### Claim Grounding States:
- `SUPPORTED`: Cited evidence substantively supports the claim ($\ge 40\%$ key concept / token overlap or direct conceptual match).
- `PARTIALLY_SUPPORTED`: Cited evidence provides partial context ($15\% - 40\%$ overlap).
- `UNSUPPORTED`: Cited evidence does not support the claim (e.g. topic mismatch, non-existent evidence IDs). Unsupported claims are stripped from final reports and excluded from scoring.

## 2. Fabricated Quote Defense
- Quotes attributed to candidate statements (e.g. "Candidate said...") are verified by `QuoteVerificationEngine` against candidate speech records in `TranscriptSegment` and code submissions.
- Exact substring matching or high-confidence token overlap ($\ge 75\%$) against candidate speech is required.
- Fabricated quotations are rejected with explicit reason logging.

## 3. Modality Authority
- **Docker Sandbox Execution**: Authoritative for runtime code correctness, test pass counts, execution time, memory usage, and runtime errors. AI cannot override sandbox results.
- **Transcript Segments**: Authoritative for spoken candidate statements.
- **Whiteboard Snapshots**: Authoritative for architecture diagram structure and component connections.
- **Resume Profile**: Authoritative for candidate prior experience claims.

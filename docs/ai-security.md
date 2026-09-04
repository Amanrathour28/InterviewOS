# AI Security & Tenant Isolation

## Security Model

AI in InterviewOS operates under zero-trust enterprise security principles:

1. **Strict Candidate Exclusion**:
   - Candidates are **never** permitted to access AI Copilot endpoints or receive AI-generated insights.
   - Guarded across three layers:
     - **API Gateway**: Verifies workspace membership and participant role (`ParticipantRole.CANDIDATE` is rejected with `HTTP 403 Forbidden`).
     - **AI Microservice**: Requires signed JWT with `is_interviewer=true`.
     - **Realtime Service**: Socket.IO events for AI are exclusively emitted to `interview:${sessionId}:interviewer`. Candidates are not subscribed to this room and cannot receive the packets.

2. **Tenant Isolation**:
   - Every AI request is tagged with a mandatory `workspace_id`.
   - Cross-tenant data leaks are blocked by checking that candidate profiles, questions, and resumes match the authenticated workspace.
   - Telemetry logs (`ai_request_logs`) are partitioned by `workspace_id` with composite indexes for audit queries.

3. **PII and Privacy Redaction**:
   - The Privacy Filter (`apps/ai/app/context/privacy_filter.py`) sanitizes data before sending it to any LLM provider:
     - Emails and phone numbers are scrubbed or tokenized.
     - Social Security Numbers and national IDs are redacted (`[REDACTED_SSN]`).
     - Credit cards and auth tokens (`Bearer ...`, `ey...`, passwords) are scrubbed.
     - Raw resume PII (addresses, photos, birthdates) is removed from prompt context.
   - Raw prompt texts and candidate outputs are **not** persisted in the database; only structured token counts, latencies, agent types, and execution status are logged.

4. **Prompt Injection Defense**:
   - Candidate code, whiteboard text, and candidate answers are treated as untrusted user inputs.
   - System prompts use strict JSON schemas, XML-style boundary delimiters (`<candidate_untrusted_input>...</candidate_untrusted_input>`), and explicit instructions that candidate text must never alter the agent's task or system prompt instructions.

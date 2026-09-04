# AI Observability & Cost Tracking

## Telemetry Architecture

Every invocation of the AI Gateway is recorded in the `ai_request_logs` PostgreSQL table and tracked in real-time.

### Database Schema (`ai_request_logs`)

```sql
CREATE TABLE ai_request_logs (
    id UUID PRIMARY KEY,
    request_id VARCHAR(36) NOT NULL,
    workspace_id VARCHAR(36),
    interview_id VARCHAR(36),
    user_id VARCHAR(36),
    agent_name VARCHAR(100),
    task_type VARCHAR(100),
    prompt_name VARCHAR(100),
    prompt_version VARCHAR(20),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    is_fallback BOOLEAN DEFAULT FALSE,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    success BOOLEAN NOT NULL,
    error_type VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_ai_request_logs_workspace_created ON ai_request_logs (workspace_id, created_at);
CREATE INDEX ix_ai_request_logs_interview_created ON ai_request_logs (interview_id, created_at);
```

## Key Metrics Tracked

1. **Provider Uptime & Availability**:
   - Primary provider success rate vs. fallback invocation frequency.
2. **End-to-End Latency**:
   - P50, P90, P99 latency broken down by agent task type.
3. **Token Consumption & Cost**:
   - Input and output token usage aggregated by workspace, organization, and interview.
4. **Agent Reliability**:
   - Parsing failure rates, schema validation retries, and fallback activation.

## Audit Access

- Workspace administrators and interviewers can query `/api/v1/ai/logs?workspace_id={id}` to view their historical usage and audit AI suggestions.
- The AI Copilot panel features a dedicated "Telemetry" tab providing instant visibility into model selection, latency, token spend, and fallback status.

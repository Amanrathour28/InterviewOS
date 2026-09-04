# AI Gateway & Provider Fallback

## Overview

The InterviewOS AI Gateway (`apps/ai/app/gateway/ai_gateway.py`) encapsulates all LLM communications behind a unified, provider-agnostic interface. It enforces retry policies, timeouts, exponential backoff, circuit breaking, and automatic fallback from cloud (Groq) to local (Ollama).

## Gateway Lifecycle

```
[Request]
   │
   ▼
[Provider Selection (Groq)]
   │
   ├──► Success ────────────────────────────────────────┐
   │                                                    │
   ▼ (Timeout / HTTP 429 / HTTP 5xx / Connection Error) │
[Fallback Handler (Ollama)]                            │
   │                                                    │
   ├──► Fallback Success ───────────────────────────────┤
   │                                                    │
   ▼ (Local failure)                                    │
[Normalized AIError Response]                           ▼
                                             [Telemetry Audit Logging]
                                                        │
                                                        ▼
                                                  [Return Result]
```

## Provider Configurations

| Provider | Purpose | Default Model | Speed | Context Window |
|---|---|---|---|---|
| **Groq (Primary)** | Fast cloud inference, deep structured reasoning | `llama-3.3-70b-versatile` | ~250–350 tok/sec | 128k tokens |
| **Groq Instant** | Ultra-low-latency short probes | `llama-3.1-8b-instant` | ~750–1200 tok/sec | 128k tokens |
| **Ollama (Fallback)** | On-premise, offline resilience | `llama3.2` | Local GPU/CPU bound | 8k–32k tokens |

## Fallback Trigger Matrix

1. **Timeout**: If the primary request exceeds `AI_TIMEOUT_SECONDS` (default: 30s), it is cancelled and redirected to Ollama.
2. **Rate Limit (`429`)**: Immediate fallback without exhausting unnecessary retry quotas.
3. **Internal Server Error (`500`, `502`, `503`, `504`)**: Exponential backoff up to `AI_MAX_RETRIES` (default: 3), then fallback.
4. **Network Unreachable**: Immediate fallback to localhost Ollama endpoint.

## Response Normalization

All providers emit normalized `AIResponse` payloads containing:
- `content`: Parsed dictionary or structured text.
- `model`: Model name used.
- `provider`: Provider identifier (`groq` or `ollama`).
- `is_fallback`: Boolean indicating whether fallback occurred.
- `input_tokens`, `output_tokens`, `total_tokens`: Token usage metrics.
- `latency_ms`: Execution time in milliseconds.

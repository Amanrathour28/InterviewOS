# Context Engine & Budgeting

## Purpose

The Context Engine (`apps/ai/app/context/builder.py` and `budgeter.py`) aggregates interview context from disparate platform services into an optimized, bounded context window for agent consumption.

## Context Window Budgeting

To avoid context overflow, ensure predictable latency, and keep token costs minimal, the budgeter enforces token allocation quotas per domain:

| Domain | Token Budget | Priority | Eviction Strategy |
|---|---|---|---|
| **System Prompt & Rubrics** | 1,500 tokens | Highest (P0) | Never evicted |
| **Job Description Core** | 800 tokens | High (P1) | Truncate boilerplate benefits/EEO |
| **Candidate Resume Summary** | 1,000 tokens | High (P1) | Keep skills and recent 3 experiences |
| **Active Problem / Code / Canvas** | 2,500 tokens | High (P1) | Truncate large boilerplate comments |
| **Interview Event History** | 1,200 tokens | Medium (P2) | Sliding window: keep stage transitions, recent notes, and last 3 Q&As |
| **Sandbox Execution Output** | 600 tokens | Medium (P2) | Keep first 5 test cases and error stack traces |

Total context window target: ~7,600 tokens (fits well within both Groq 128k and Ollama 8k/32k models).

## Context Aggregation Flow

```
1. Fetch Interview Session State (stages, timing, participants)
2. Fetch Candidate Profile & Parsed Resume Data
3. Fetch Job Requirements & Competency Targets
4. Fetch Active Workspace State (Monaco code buffer, tldraw canvas JSON)
5. Fetch Sandbox Execution Results (if in coding stage)
6. Apply Privacy Filter (redact PII and auth secrets)
7. Apply Budgeter (truncate over-budget sections according to priority)
8. Assemble Immutable InterviewContext dataclass for Agent execution
```

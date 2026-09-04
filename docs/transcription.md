# Transcription Pipeline & Response Boundary Detection — Phase 14

## Architecture

```
WebRTC Audio Stream / Speech Audio
               │
               ▼
       Segment Ingestion & Chunking
               │
               ▼
     Speaker Attribution (Candidate vs Interviewer)
               │
               ▼
     Response Boundary Detector
   ┌───────────┴───────────┐
   ▼                       ▼
Interim Streaming     Final Segment
(CONTINUING)          (COMPLETE)
               │
               ▼
       LiveInterviewContext
```

## Response Boundary States

1. `RESPONSE_STARTED`: Initial tokens detected from speaker.
2. `RESPONSE_CONTINUING`: Interim transcript streaming or speech below minimum thought threshold.
3. `RESPONSE_COMPLETE`: Terminal punctuation reached, silence threshold exceeded, or interviewer turn change.
4. `RESPONSE_INTERRUPTED`: Speaker role changed before segment completion.

## Debouncing & Latency Budget

To optimize token usage and avoid redundant LLM invocations, expensive reasoning graph evaluations only fire upon reaching `RESPONSE_COMPLETE` or explicit interviewer manual trigger.

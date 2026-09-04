# AI Interviewer Architecture — Phase 14

## Overview

The AI Interviewer Copilot in InterviewOS is a real-time, evidence-grounded intelligence layer. It analyzes live interview streams (transcripts, coding submissions, whiteboard changes, and chat) and provides structured, bounded recommendations to the human interviewer.

```
                    LIVE INTERVIEW
                         │
        ┌────────────────┼────────────────┐
        │                │                │
      Audio            Chat             Code
        │                │                │
        ▼                ▼                ▼
    Transcript       Messages        Code Events
        │                │                │
        └────────────────┼────────────────┘
                         ▼
              REAL-TIME INTERVIEW CONTEXT
                         │
                         ▼
               CONTEXT NORMALIZATION
                         │
                         ▼
              PRIVACY / AUTHORIZATION
                         │
                         ▼
             ADAPTIVE INTERVIEW ENGINE
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    Next Question    Follow-up      Difficulty
      Selection      Generation     Adaptation
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                 INTERVIEW STRATEGY
                         │
                         ▼
                  AI RECOMMENDATION
                         │
                         ▼
              INTERVIEWER CONTROL CENTER
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
             Accept              Reject
               │
               ▼
          Ask / Modify
               │
               ▼
       Durable Interview Event
```

## Core Principles

1. **Human-in-the-Loop Authority**: The AI is strictly assistive. It never speaks autonomously or mutates interview states independently. Every recommendation requires explicit interviewer approval.
2. **Question Plan Boundedness**: Recommendations respect the approved Question Plan, ensuring questions stay within pre-approved competencies and difficulty limits.
3. **Evidence Grounding**: Questions target candidate statements, resume claims, and verified code execution results.
4. **Resilience & Fallback**: System functions in manual mode seamlessly if AI services encounter latency or provider downtime.

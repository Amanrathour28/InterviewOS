"""
Context Window Budgeter.

Prevents unbounded prompt growth by implementing explicit context budgeting.
Every AI request has a maximum token budget. The budgeter selects, prioritizes,
and summarizes context to fit within that budget.

Priority ordering (highest → lowest):
  1. Current stage information
  2. Recent events (last 10)
  3. Current problem / question context
  4. Candidate profile (filtered)
  5. Job requirements (filtered)
  6. Older events (summarized or truncated)

Future phases may add:
  - LLM-based summarization of older context
  - Semantic search for relevant past events
"""

import logging
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("interviewos.ai.budgeter")


def estimate_chars(obj: Any) -> int:
    """Rough character count estimate for budget tracking."""
    if obj is None:
        return 0
    if isinstance(obj, str):
        return len(obj)
    if isinstance(obj, (dict, list)):
        return len(str(obj))
    return len(str(obj))


def budget_events(
    events: List[Dict],
    max_events: int = 50,
    max_recent: int = 10,
    budget_chars: int = 6000,
) -> List[Dict]:
    """
    Select events within budget:
    - Always include the last max_recent events (most important)
    - Fill remaining budget with older events (newest first)
    - Stop when budget is exhausted
    """
    if not events:
        return []

    # Always take the most recent events first
    recent = events[-max_recent:]
    older = events[:-max_recent]

    used_chars = sum(estimate_chars(e) for e in recent)
    selected = list(recent)

    # Add older events if budget allows
    for event in reversed(older):
        event_size = estimate_chars(event)
        if used_chars + event_size > budget_chars:
            break
        selected.insert(0, event)
        used_chars += event_size

    logger.debug(
        "Context budgeter: selected %d/%d events, ~%d chars",
        len(selected), len(events), used_chars,
    )
    return selected


def truncate_text(text: str, max_chars: int, suffix: str = "... [truncated]") -> str:
    """Truncate a text field to max_chars, appending suffix if truncated."""
    if not text or len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def budget_candidate_content(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Truncate long candidate text fields to prevent unbounded prompts.
    """
    result = dict(candidate)
    max_chars = settings.AI_MAX_CANDIDATE_CONTENT_CHARS

    for field in ("education_summary", "notes_summary"):
        if field in result and isinstance(result[field], str):
            result[field] = truncate_text(result[field], max_chars // 2)

    return result


def budget_job_description(job: Dict[str, Any]) -> Dict[str, Any]:
    """Truncate job description fields."""
    result = dict(job)
    if "description" in result and isinstance(result["description"], str):
        result["description"] = truncate_text(result["description"], 3000)
    return result


def budget_code_content(code: str) -> str:
    """Truncate code to prevent oversized prompts."""
    return truncate_text(code, 4000)


def build_context_summary(
    candidate: Optional[Dict] = None,
    job: Optional[Dict] = None,
    session: Optional[Dict] = None,
    events: Optional[List[Dict]] = None,
    current_problem: Optional[Dict] = None,
    current_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assemble a budgeted context dictionary for use in prompts.
    All fields are size-capped to prevent unbounded growth.
    """
    context: Dict[str, Any] = {}

    if current_stage:
        context["current_stage"] = current_stage

    if session:
        context["session"] = {
            k: session.get(k)
            for k in ("id", "status", "started_at", "total_paused_seconds")
            if session.get(k) is not None
        }

    if candidate:
        context["candidate"] = budget_candidate_content(candidate)

    if job:
        context["job"] = budget_job_description(job)

    if events:
        context["recent_events"] = budget_events(
            events,
            max_events=settings.AI_MAX_CONTEXT_EVENTS,
            budget_chars=4000,
        )

    if current_problem:
        context["current_problem"] = {
            "title": current_problem.get("title", ""),
            "difficulty": current_problem.get("difficulty", ""),
            "category": current_problem.get("category", ""),
            # Truncate problem statement to 1500 chars
            "statement": truncate_text(
                current_problem.get("problem_statement", ""), 1500
            ),
        }

    return context

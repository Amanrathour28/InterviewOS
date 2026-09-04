"""
InterviewContext Builder.

Converts raw interview telemetry into structured AI context.
Applies privacy filtering and context budgeting before returning.

The resulting InterviewContext is the primary input to all agents.
It is the ONLY approved way to assemble AI context — agents must not
query raw database tables directly.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.context.budgeter import build_context_summary
from app.context.privacy_filter import (
    filter_candidate,
    filter_events,
    filter_job,
    filter_session,
    label_untrusted_content,
)

logger = logging.getLogger("interviewos.ai.context")


@dataclass
class InterviewContext:
    """
    Structured, filtered, budgeted context for an AI agent request.
    All data here has passed through the privacy filter.
    """

    # Required tenant context (for isolation enforcement)
    workspace_id: str
    interview_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    # Interview metadata
    current_stage: Optional[str] = None
    elapsed_seconds: int = 0

    # Filtered data
    candidate: Dict[str, Any] = field(default_factory=dict)
    job: Dict[str, Any] = field(default_factory=dict)
    session: Dict[str, Any] = field(default_factory=dict)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)

    # Coding context
    current_problem: Optional[Dict[str, Any]] = None
    candidate_code: Optional[str] = None  # Labeled UNTRUSTED in prompts
    execution_result: Optional[Dict[str, Any]] = None  # Authoritative — from sandbox

    # Whiteboard context
    whiteboard_state: Optional[Dict[str, Any]] = None

    # Previous questions (to avoid duplicates)
    previous_questions: List[str] = field(default_factory=list)

    def to_prompt_dict(self) -> Dict[str, Any]:
        """
        Serialize context to a dict suitable for prompt assembly.
        Candidate code is explicitly labeled as UNTRUSTED.
        """
        d: Dict[str, Any] = {
            "workspace_id": self.workspace_id,
            "interview_id": self.interview_id,
            "session_id": self.session_id,
            "current_stage": self.current_stage,
            "elapsed_seconds": self.elapsed_seconds,
        }

        if self.candidate:
            d["candidate"] = self.candidate

        if self.job:
            d["job"] = self.job

        if self.session:
            d["session"] = self.session

        if self.recent_events:
            d["recent_events"] = self.recent_events

        if self.current_problem:
            d["current_problem"] = self.current_problem

        if self.execution_result:
            # Execution result is AUTHORITATIVE — label it explicitly
            d["execution_result"] = {
                **self.execution_result,
                "_note": "This is the authoritative sandbox result. Do not contradict it.",
            }

        if self.whiteboard_state:
            d["whiteboard_state"] = self.whiteboard_state

        if self.previous_questions:
            d["previous_questions"] = self.previous_questions

        # Candidate code is labeled UNTRUSTED
        if self.candidate_code:
            d["candidate_code"] = label_untrusted_content(
                self.candidate_code, "CANDIDATE_CODE"
            )

        return d

    def to_prompt_json(self, indent: int = 2) -> str:
        """Return JSON string of the prompt-safe context dict."""
        return json.dumps(self.to_prompt_dict(), indent=indent, default=str)


class InterviewContextBuilder:
    """
    Assembles an InterviewContext from raw interview service data.
    Applies privacy filtering and context budgeting.
    """

    def build(
        self,
        workspace_id: str,
        interview_id: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        current_stage: Optional[str] = None,
        elapsed_seconds: int = 0,
        raw_candidate: Optional[Dict] = None,
        raw_job: Optional[Dict] = None,
        raw_session: Optional[Dict] = None,
        raw_events: Optional[List[Dict]] = None,
        current_problem: Optional[Dict] = None,
        candidate_code: Optional[str] = None,
        execution_result: Optional[Dict] = None,
        whiteboard_state: Optional[Dict] = None,
        previous_questions: Optional[List[str]] = None,
    ) -> InterviewContext:
        """
        Build a filtered, budgeted InterviewContext.

        Args:
            raw_*: Unfiltered data from the database / API
            All raw data is passed through privacy_filter before being stored.
        """

        # Apply privacy filters
        filtered_candidate = filter_candidate(raw_candidate or {})
        filtered_job = filter_job(raw_job or {})
        filtered_session = filter_session(raw_session or {})
        filtered_events = filter_events(raw_events or [])

        # Apply budget (modifies fields in place)
        budgeted = build_context_summary(
            candidate=filtered_candidate,
            job=filtered_job,
            session=filtered_session,
            events=filtered_events,
            current_problem=current_problem,
            current_stage=current_stage,
        )

        return InterviewContext(
            workspace_id=workspace_id,
            interview_id=interview_id,
            session_id=session_id,
            user_id=user_id,
            current_stage=current_stage,
            elapsed_seconds=elapsed_seconds,
            candidate=budgeted.get("candidate", {}),
            job=budgeted.get("job", {}),
            session=budgeted.get("session", {}),
            recent_events=budgeted.get("recent_events", []),
            current_problem=budgeted.get("current_problem"),
            candidate_code=candidate_code,
            execution_result=execution_result,
            whiteboard_state=whiteboard_state,
            previous_questions=previous_questions or [],
        )

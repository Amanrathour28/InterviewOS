"""
Deterministic Interview Tools.

Tools are deterministic functions that agents may call to fetch data.
They do NOT call the LLM — they query structured data sources.

SECURITY RULES:
  - Every tool receives and validates authorized context (workspace_id, interview_id)
  - Tools never expose raw SQL access to agents
  - Tools never access arbitrary database tables
  - Tools enforce workspace scoping on every query
  - Tools never return secrets, credentials, or private data

These tools are designed for LangGraph tool_node integration (Phase 14+).
In Phase 12, agents call them directly through AgentContext.
"""

import logging
from typing import Any, Dict, List, Optional
from app.gateway.errors import AITenantIsolationError

logger = logging.getLogger("interviewos.ai.tools")


def _verify_workspace(
    resource_workspace_id: str,
    caller_workspace_id: str,
    resource_name: str,
) -> None:
    """Verify that a resource belongs to the caller's workspace."""
    if resource_workspace_id != caller_workspace_id:
        raise AITenantIsolationError(
            f"{resource_name} workspace {resource_workspace_id!r} does not match "
            f"caller workspace {caller_workspace_id!r}"
        )


class InterviewTools:
    """
    Deterministic tools providing agents with read-only access to interview data.
    All methods are workspace-scoped and enforce tenant isolation.

    In Phase 14+, these will be registered as LangChain tools for autonomous agents.
    In Phase 12, they are called directly from agent code.
    """

    def get_candidate_profile(
        self,
        candidate_data: Dict[str, Any],
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Return filtered candidate profile fields relevant for interview prep."""
        from app.context.privacy_filter import filter_candidate

        candidate_workspace = candidate_data.get("workspace_id", workspace_id)
        _verify_workspace(candidate_workspace, workspace_id, "Candidate")

        return filter_candidate(candidate_data)

    def get_job_requirements(
        self,
        job_data: Dict[str, Any],
        workspace_id: str,
    ) -> Dict[str, Any]:
        """Return filtered job fields relevant for interview prep."""
        from app.context.privacy_filter import filter_job

        job_workspace = job_data.get("workspace_id", workspace_id)
        _verify_workspace(job_workspace, workspace_id, "Job")

        return filter_job(job_data)

    def get_recent_events(
        self,
        events: List[Dict[str, Any]],
        workspace_id: str,
        session_id: str,
        max_events: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return the most recent filtered interview events for a session."""
        from app.context.privacy_filter import filter_events

        # Verify all events belong to the specified session
        session_events = [
            e for e in events
            if e.get("session_id") == session_id or "session_id" not in e
        ]

        return filter_events(session_events, max_events=max_events)

    def get_execution_result(
        self,
        execution_result: Optional[Dict[str, Any]],
        workspace_id: str,
        note: str = "Authoritative sandbox result — cannot be overridden by AI",
    ) -> Optional[Dict[str, Any]]:
        """
        Return the execution result with an authoritative label.
        This result CANNOT be contradicted by AI analysis.
        """
        if not execution_result:
            return None

        return {
            **execution_result,
            "_authoritative": True,
            "_note": note,
        }

    def get_question_history(
        self,
        events: List[Dict[str, Any]],
        workspace_id: str,
    ) -> List[str]:
        """Extract the list of questions asked in this interview session."""
        questions = []
        for event in events:
            if event.get("event_type") == "QUESTION_ASKED":
                payload = event.get("payload", {})
                question_text = payload.get("question") or payload.get("question_text")
                if question_text:
                    questions.append(question_text)
        return questions

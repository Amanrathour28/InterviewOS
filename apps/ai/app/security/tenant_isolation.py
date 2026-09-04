"""
Tenant Isolation Enforcement.

Every AI request must carry workspace/session/interview identifiers.
This module validates that context data belongs to the claimed workspace.

Isolation Rules:
  - workspace_id in context must match workspace_id in the request
  - session_id must belong to the claimed interview_id
  - AI tool calls must verify ownership before fetching any data
  - Never allow one workspace's data to appear in another's AI context

These checks are in ADDITION to the main API's RBAC checks.
They run server-side in the AI service.
"""

import logging
from typing import Optional
from app.gateway.errors import AITenantIsolationError, AIUnauthorizedError

logger = logging.getLogger("interviewos.ai.security")


def assert_workspace_match(
    context_workspace_id: str,
    request_workspace_id: str,
    operation: str = "AI request",
) -> None:
    """
    Assert that the context data belongs to the same workspace as the request.
    Raises AITenantIsolationError if there is a mismatch.
    This should NEVER happen in normal operation.
    """
    if context_workspace_id != request_workspace_id:
        logger.error(
            "TENANT ISOLATION VIOLATION in %s: context workspace=%s, request workspace=%s",
            operation,
            context_workspace_id,
            request_workspace_id,
        )
        raise AITenantIsolationError(
            f"Context workspace {context_workspace_id!r} does not match "
            f"request workspace {request_workspace_id!r}"
        )


def assert_interviewer_only(
    is_interviewer: bool,
    operation: str = "AI operation",
) -> None:
    """
    Assert that the caller is an interviewer (not a candidate).
    Candidates must never access AI insights, suggestions, or copilot data.
    """
    if not is_interviewer:
        logger.warning("Candidate attempted to access interviewer-only AI: %s", operation)
        raise AIUnauthorizedError(
            f"Operation {operation!r} is restricted to interviewers only"
        )


def sanitize_request_metadata(metadata: dict) -> dict:
    """
    Remove any sensitive fields from request metadata before logging.
    Metadata is stored in ai_request_logs — must not contain secrets.
    """
    blocked = {
        "api_key", "secret", "password", "token", "credential",
        "authorization", "auth", "key",
    }
    return {
        k: v for k, v in metadata.items()
        if k.lower() not in blocked and isinstance(v, (str, int, float, bool, type(None)))
    }

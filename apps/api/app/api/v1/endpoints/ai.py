"""
AI Copilot Proxy Endpoints — Phase 12.

Proxies requests to the AI Service, enforcing:
1. User authentication (JWT)
2. Workspace access verification
3. Interview participant check (only interviewers/hosts can access AI copilot, NOT candidates)
4. Telemetry audit retrieval
"""

import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    verify_interview_access,
    verify_workspace_access,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.models.ai import AIRequestLog
from app.models.interview import Interview, InterviewParticipant, ParticipantRole
from app.models.user import User, UserRole

logger = logging.getLogger("interviewos.api.ai")
router = APIRouter(prefix="/ai", tags=["AI Copilot & Gateway"])


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class AITaskProxyRequest(BaseModel):
    interview_id: str
    workspace_id: str
    task_type: str
    session_id: Optional[str] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)


class QuestionGenProxyRequest(BaseModel):
    interview_id: str
    workspace_id: str
    session_id: Optional[str] = None
    difficulty: str = "medium"
    question_type: str = "technical"
    topic_focus: Optional[str] = None
    topics_covered: List[str] = Field(default_factory=list)
    candidate: Optional[Dict[str, Any]] = None
    job: Optional[Dict[str, Any]] = None
    previous_questions: List[str] = Field(default_factory=list)
    current_stage: Optional[str] = None


class FollowUpProxyRequest(BaseModel):
    interview_id: str
    workspace_id: str
    question_asked: str
    candidate_answer: str
    session_id: Optional[str] = None
    target_skill: Optional[str] = None
    difficulty: str = "medium"
    remaining_seconds: int = 600


class ResumeAnalysisProxyRequest(BaseModel):
    interview_id: str
    workspace_id: str
    resume_text: Optional[str] = None
    candidate_profile: Optional[Dict[str, Any]] = None
    job: Optional[Dict[str, Any]] = None


class JobAnalysisProxyRequest(BaseModel):
    interview_id: str
    workspace_id: str
    job: Dict[str, Any]


class CodingAnalysisProxyRequest(BaseModel):
    interview_id: str
    workspace_id: str
    session_id: Optional[str] = None
    problem: Optional[Dict[str, Any]] = None
    candidate_code: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    submission_history: List[Dict[str, Any]] = Field(default_factory=list)


class SystemDesignProxyRequest(BaseModel):
    interview_id: str
    workspace_id: str
    session_id: Optional[str] = None
    whiteboard_state: Optional[Dict[str, Any]] = None
    candidate_explanation: Optional[str] = None
    problem_statement: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper: Verify Interviewer Access and Proxy to AI Service
# ---------------------------------------------------------------------------

async def _ensure_interviewer_access(
    interview_id_str: str,
    workspace_id_str: str,
    current_user: User,
    db: AsyncSession,
) -> None:
    """
    Ensure the caller has access to the workspace and is an interviewer.
    Candidates MUST be blocked with 403.
    """
    if current_user.role == UserRole.PLATFORM_ADMIN:
        return

    try:
        w_uuid = uuid.UUID(workspace_id_str)
        i_uuid = uuid.UUID(interview_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format for workspace_id or interview_id",
        )

    # 1. Verify workspace membership
    await verify_workspace_access(w_uuid, current_user, db)

    # 2. Check if user is a candidate participant in this interview
    stmt = select(InterviewParticipant).where(
        InterviewParticipant.interview_id == i_uuid,
        InterviewParticipant.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    participant = res.scalar_one_or_none()

    if participant and participant.role == ParticipantRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI Copilot features are restricted to interviewers",
        )


async def _proxy_ai_request(endpoint: str, payload: dict, current_user: User) -> dict:
    """Forward request to AI Service with minted JWT claims."""
    url = f"{settings.AI_SERVICE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    token = create_access_token(
        subject=str(current_user.id),
        extra_claims={
            "workspace_id": payload.get("workspace_id"),
            "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            "is_interviewer": True,
        },
        expires_delta=timedelta(minutes=5),
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=float(settings.AI_TIMEOUT_SECONDS)) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=resp.json().get("detail", "Access forbidden by AI service"),
                )
            if resp.status_code >= 400:
                logger.warning("AI service error %d: %s", resp.status_code, resp.text)
                return {
                    "status": "failed",
                    "error_message": f"AI service error ({resp.status_code})",
                    "output": None,
                }
            return resp.json()
    except httpx.RequestError as exc:
        logger.error("AI service unreachable at %s: %s", url, exc)
        return {
            "status": "failed",
            "error_message": f"AI service unreachable: {str(exc)}",
            "output": None,
        }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/tasks")
async def run_ai_task(
    req: AITaskProxyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_interviewer_access(req.interview_id, req.workspace_id, current_user, db)
    return await _proxy_ai_request("ai/tasks", req.model_dump(), current_user)


@router.post("/generate-question")
async def generate_question(
    req: QuestionGenProxyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_interviewer_access(req.interview_id, req.workspace_id, current_user, db)
    return await _proxy_ai_request("ai/generate-question", req.model_dump(), current_user)


@router.post("/generate-follow-up")
async def generate_follow_up(
    req: FollowUpProxyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_interviewer_access(req.interview_id, req.workspace_id, current_user, db)
    return await _proxy_ai_request("ai/generate-follow-up", req.model_dump(), current_user)


@router.post("/analyze-resume")
async def analyze_resume(
    req: ResumeAnalysisProxyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_interviewer_access(req.interview_id, req.workspace_id, current_user, db)
    return await _proxy_ai_request("ai/analyze-resume", req.model_dump(), current_user)


@router.post("/analyze-job")
async def analyze_job(
    req: JobAnalysisProxyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_interviewer_access(req.interview_id, req.workspace_id, current_user, db)
    return await _proxy_ai_request("ai/analyze-job", req.model_dump(), current_user)


@router.post("/analyze-coding")
async def analyze_coding(
    req: CodingAnalysisProxyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_interviewer_access(req.interview_id, req.workspace_id, current_user, db)
    return await _proxy_ai_request("ai/analyze-coding", req.model_dump(), current_user)


@router.post("/analyze-system-design")
async def analyze_system_design(
    req: SystemDesignProxyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_interviewer_access(req.interview_id, req.workspace_id, current_user, db)
    return await _proxy_ai_request("ai/analyze-system-design", req.model_dump(), current_user)


@router.get("/health")
async def ai_health(current_user: User = Depends(get_current_user)):
    """Check AI service connectivity and provider status."""
    url = f"{settings.AI_SERVICE_URL.rstrip('/')}/health"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            return resp.json()
    except Exception as exc:
        return {
            "status": "degraded",
            "service": "ai-service",
            "error": str(exc),
        }


@router.get("/logs")
async def get_ai_logs(
    workspace_id: str = Query(...),
    interview_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve telemetry log for AI requests within a workspace."""
    try:
        w_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workspace UUID")

    await verify_workspace_access(w_uuid, current_user, db)

    query = (
        select(AIRequestLog)
        .where(AIRequestLog.workspace_id == workspace_id)
        .order_by(desc(AIRequestLog.created_at))
        .limit(limit)
    )
    if interview_id:
        query = query.where(AIRequestLog.interview_id == interview_id)

    res = await db.execute(query)
    logs = res.scalars().all()

    return [
        {
            "id": str(log.id),
            "request_id": log.request_id,
            "workspace_id": log.workspace_id,
            "interview_id": log.interview_id,
            "agent_name": log.agent_name,
            "task_type": log.task_type,
            "provider": log.provider,
            "model": log.model,
            "is_fallback": log.is_fallback,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "total_tokens": log.total_tokens,
            "latency_ms": log.latency_ms,
            "success": log.success,
            "error_type": log.error_type,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

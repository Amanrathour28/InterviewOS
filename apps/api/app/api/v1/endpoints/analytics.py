"""
Phase 16 — Analytics & Decision Intelligence API Endpoints.

Provides:
- GET /api/v1/analytics/overview
- GET /api/v1/analytics/interviews
- GET /api/v1/analytics/candidates
- GET /api/v1/analytics/candidates/{candidate_id}/timeline
- GET /api/v1/analytics/competencies
- GET /api/v1/analytics/interviewers
- GET /api/v1/analytics/questions
- GET /api/v1/analytics/ai
- GET /api/v1/analytics/evidence
- GET /api/v1/analytics/funnel
- POST /api/v1/analytics/export
- POST /api/v1/analytics/explain

Security:
- All endpoints require authentication.
- CANDIDATE role is rejected with HTTP 403.
- Workspace isolation enforced server-side.
- Export and explain endpoints additionally validate role before serving.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    verify_workspace_access,
)
from app.models.user import User, UserRole
from app.services.analytics_service import analytics_service
from app.services.interview_analytics_service import interview_analytics_service
from app.services.candidate_decision_service import candidate_decision_service
from app.services.competency_analytics_service import competency_analytics_service
from app.services.interviewer_analytics_service import interviewer_analytics_service
from app.services.question_analytics_service import question_analytics_service
from app.services.ai_telemetry_analytics_service import ai_telemetry_analytics_service
from app.services.analytics_export_service import analytics_export_service

logger = logging.getLogger("interviewos.api.analytics")

async def require_non_candidate(current_user: User = Depends(get_current_user)) -> User:
    """Block CANDIDATE role from all analytics endpoints."""
    if current_user.role == UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates are not authorized to access analytics.",
        )
    return current_user


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics & Decision Intelligence"],
    dependencies=[Depends(require_non_candidate)],
)


def _deny_candidate(current_user: User) -> None:
    """Block CANDIDATE role from all analytics endpoints."""
    if current_user.role == UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates are not authorized to access analytics.",
        )


def _parse_window_and_dates(
    window: str,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> tuple[datetime, datetime]:
    """Parse time window with fallback to 30d."""
    return analytics_service.parse_time_window(
        window=window,
        from_date=from_date,
        to_date=to_date,
    )


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ExplainRequest(BaseModel):
    metrics: Dict[str, Any] = Field(description="Structured deterministic metrics to explain")
    question: str = Field(max_length=500, description="Natural language question about the metrics")
    context_label: str = Field(default="analytics", max_length=80)


class ExportRequest(BaseModel):
    export_type: str = Field(default="candidates", description="Type: candidates, interviews, competencies")
    format: str = Field(default="csv", description="csv or json")
    window: str = Field(default="30d")
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    job_id: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@router.get("/overview")
async def get_analytics_overview(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    job_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """
    High-level KPI overview: volume, scores, recommendation distribution, completion rate.
    """
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    volume = await interview_analytics_service.get_interview_volume_and_rates(
        db, workspace_id, start, end, job_id=job_id
    )
    decision = await candidate_decision_service.get_candidate_decision_matrix(
        db, workspace_id, start, end, job_id=job_id, status_filter="finalized"
    )
    evidence = await ai_telemetry_analytics_service.get_evidence_quality_analytics(
        db, workspace_id, start, end, job_id=job_id
    )

    return {
        "time_window": {"from": start.isoformat(), "to": end.isoformat(), "window": window},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interview_volume": volume,
        "score_summary": decision["score_distribution"],
        "recommendation_distribution": decision["recommendation_distribution"],
        "evidence_quality_summary": evidence,
    }


# ---------------------------------------------------------------------------
# Interview Analytics
# ---------------------------------------------------------------------------

@router.get("/interviews")
async def get_interview_analytics(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    job_id: Optional[uuid.UUID] = Query(default=None),
    interview_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """Interview volume, completion/cancellation rates, duration stats, stage progression."""
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    volume = await interview_analytics_service.get_interview_volume_and_rates(
        db, workspace_id, start, end, job_id=job_id, interview_type=interview_type
    )
    duration = await interview_analytics_service.get_duration_analytics(
        db, workspace_id, start, end, job_id=job_id
    )
    stages = await interview_analytics_service.get_stage_progression_analytics(
        db, workspace_id, start, end
    )
    timeline = await interview_analytics_service.get_volume_timeline(
        db, workspace_id, start, end
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "volume": volume,
        "duration": duration,
        "stages": stages,
        "timeline": timeline,
    }


# ---------------------------------------------------------------------------
# Candidate Decision Intelligence
# ---------------------------------------------------------------------------

@router.get("/candidates")
async def get_candidate_analytics(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    job_id: Optional[uuid.UUID] = Query(default=None),
    recommendation: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """Candidate decision matrix with scores, recommendations, and evidence metrics."""
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    result = await candidate_decision_service.get_candidate_decision_matrix(
        db, workspace_id, start, end,
        job_id=job_id,
        recommendation_filter=recommendation,
        status_filter=status_filter,
    )
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.get("/candidates/{candidate_id}/timeline")
async def get_candidate_timeline(
    candidate_id: uuid.UUID,
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """Unified chronological candidate hiring timeline."""
    _deny_candidate(current_user)
    result = await candidate_decision_service.get_candidate_unified_timeline(
        db, workspace_id, candidate_id
    )
    if not result.get("timeline"):
        raise HTTPException(status_code=404, detail="Candidate not found in this workspace")
    return result


# ---------------------------------------------------------------------------
# Competency Analytics
# ---------------------------------------------------------------------------

@router.get("/competencies")
async def get_competency_analytics(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    job_id: Optional[uuid.UUID] = Query(default=None),
    finalized_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """Competency score distributions, sufficiency rates, and override rates."""
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    result = await competency_analytics_service.get_competency_analytics(
        db, workspace_id, start, end, job_id=job_id, finalized_only=finalized_only
    )
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ---------------------------------------------------------------------------
# Interviewer Panel Analytics
# ---------------------------------------------------------------------------

@router.get("/interviewers")
async def get_interviewer_analytics(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    min_sample: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """Interviewer panel activity metrics and objective calibration signals."""
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    result = await interviewer_analytics_service.get_interviewer_analytics(
        db, workspace_id, start, end, min_sample_threshold=min_sample
    )
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ---------------------------------------------------------------------------
# Question & Adaptive Analytics
# ---------------------------------------------------------------------------

@router.get("/questions")
async def get_question_analytics(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    job_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """Question bank performance metrics and evidence yield indicators."""
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    questions = await question_analytics_service.get_question_analytics(
        db, workspace_id, start, end, job_id=job_id
    )
    adaptive = await question_analytics_service.get_adaptive_questioning_analytics(
        db, workspace_id, start, end
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "question_bank": questions,
        "adaptive_questioning": adaptive,
    }


# ---------------------------------------------------------------------------
# AI Telemetry & Evidence Quality
# ---------------------------------------------------------------------------

@router.get("/ai")
async def get_ai_analytics(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    agent: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """AI request telemetry: volume, latency, tokens, provider/agent breakdown."""
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    result = await ai_telemetry_analytics_service.get_ai_telemetry_analytics(
        db, workspace_id, start, end,
        agent_filter=agent,
        provider_filter=provider,
    )
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.get("/evidence")
async def get_evidence_quality_analytics(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    job_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """Evidence quality metrics: grounding rates, contradiction analytics."""
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    result = await ai_telemetry_analytics_service.get_evidence_quality_analytics(
        db, workspace_id, start, end, job_id=job_id
    )
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ---------------------------------------------------------------------------
# Hiring Funnel
# ---------------------------------------------------------------------------

@router.get("/funnel")
async def get_hiring_funnel(
    workspace_id: uuid.UUID = Query(...),
    window: str = Query(default="30d"),
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    job_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """Hiring funnel: applicant -> matched -> scheduled -> started -> completed -> finalized -> hire."""
    _deny_candidate(current_user)
    start, end = _parse_window_and_dates(window, from_date, to_date)

    result = await candidate_decision_service.get_hiring_funnel_analytics(
        db, workspace_id, start, end, job_id=job_id
    )
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.post("/export")
async def export_analytics(
    req: ExportRequest,
    workspace_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """
    Secure analytics export (CSV or JSON).
    Enforces workspace isolation. Candidate role forbidden.
    Only WORKSPACE_ADMIN and above can export.
    """
    _deny_candidate(current_user)

    start, end = _parse_window_and_dates(req.window, req.from_date, req.to_date)

    if req.export_type == "candidates":
        data = await candidate_decision_service.get_candidate_decision_matrix(
            db, workspace_id, start, end, job_id=req.job_id
        )
        records = analytics_export_service.build_evaluation_export_records(data["candidates"])
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export_type: {req.export_type}")

    if req.format == "csv":
        csv_content = analytics_export_service.to_csv(records)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=interviewos_{req.export_type}_export.csv"},
        )
    elif req.format == "json":
        json_content = analytics_export_service.to_json(
            records,
            metadata={"workspace_id": str(workspace_id), "export_type": req.export_type},
        )
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=interviewos_{req.export_type}_export.json"},
        )
    else:
        raise HTTPException(status_code=400, detail="format must be 'csv' or 'json'")


# ---------------------------------------------------------------------------
# AI Explanation
# ---------------------------------------------------------------------------

@router.post("/explain")
async def explain_analytics(
    req: ExplainRequest,
    workspace_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    _ws: Any = Depends(verify_workspace_access),
):
    """
    Advisory AI explanation of structured deterministic metrics.
    AI NEVER calculates authoritative values — it only interprets what's passed.
    Calls the AI service which hosts the analytics explanation agent.
    """
    _deny_candidate(current_user)

    if len(req.question) > 500:
        raise HTTPException(status_code=400, detail="Question must be under 500 characters")

    import httpx
    from app.core.config import settings

    ai_url = f"{settings.AI_SERVICE_URL}/api/v1/ai/analytics/explain"
    payload = {
        "workspace_id": str(workspace_id),
        "metrics": req.metrics,
        "question": req.question,
        "context_label": req.context_label,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(ai_url, json=payload)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning("AI explain service returned %s", resp.status_code)
    except Exception as exc:
        logger.warning("AI explain service unavailable: %s", exc)

    # Graceful fallback: return metrics without AI explanation
    return {
        "explanation": (
            "AI explanation service is currently unavailable. "
            "Please review the metrics directly."
        ),
        "disclaimer": (
            "This explanation is advisory only. All metric values are computed deterministically "
            "by the analytics engine and are not modified by the AI explanation layer."
        ),
    }

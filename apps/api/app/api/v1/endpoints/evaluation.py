"""
Phase 15 — Evidence-Based Evaluation & Reporting API Endpoints.

Enforces:
- Strict candidate access denial (HTTP 403)
- Tenant & workspace authorization
- Human review and immutable finalization gates
- Audited score overrides
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    verify_interview_access,
    verify_workspace_access,
)
from app.models.evaluation import (
    ContradictionSeverity,
    Evaluation,
    EvaluationCompetencyScore,
    EvaluationContradiction,
    EvaluationEvidence,
    EvaluationScoreInput,
    EvaluationStatus,
    HiringRecommendation,
)
from app.models.user import User, UserRole
from app.services.evaluation_service import evaluation_service
from app.services.evidence_service import evidence_service

logger = logging.getLogger("interviewos.api.evaluation_endpoints")

router = APIRouter(prefix="/interviews", tags=["Interview Evaluation"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class OverrideScoreRequest(BaseModel):
    new_rubric_level: Optional[float] = Field(None, ge=1.0, le=5.0, description="New rubric level (1.0 to 5.0)")
    overridden_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="New numerical score (0 to 100)")
    rationale: Optional[str] = Field(None, description="Mandatory reason for score override")
    override_reason: Optional[str] = Field(None, description="Alias for rationale")

    def get_rubric_level(self) -> float:
        if self.new_rubric_level is not None:
            return self.new_rubric_level
        if self.overridden_score is not None:
            return evaluation_scoring_service.score_to_rubric_level(self.overridden_score)
        return 3.0

    def get_rationale(self) -> str:
        return self.rationale or self.override_reason or "Score override by reviewer."


class GenerateEvaluationRequest(BaseModel):
    session_id: Optional[uuid.UUID] = None


class CompetencyScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evaluation_id: uuid.UUID
    competency_name: str
    rubric_level: float
    calculated_score: float
    weight: float
    confidence: float
    status: str
    rationale: str
    observed_facts: List[str]
    inferences: List[str]
    evidence_ids: List[str]
    is_overridden: bool
    original_ai_rubric_level: Optional[float] = None
    override_reason: Optional[str] = None
    overridden_at: Optional[datetime] = None


class ContradictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evaluation_id: uuid.UUID
    type: str
    severity: str
    source_a_type: str
    source_a_description: str
    source_b_type: str
    source_b_description: str
    description: str
    resolution: Optional[str] = None
    is_resolved: bool


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    interview_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    status: str
    version: int
    overall_score: float
    overall_rubric_level: float
    confidence: float
    recommendation: str
    summary: Optional[str] = None
    strengths: List[Dict[str, Any]]
    development_areas: List[Dict[str, Any]]
    evidence_gaps: List[Dict[str, Any]]
    is_locked: bool
    reviewed_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    competency_scores: List[CompetencyScoreResponse] = Field(default_factory=list)
    contradictions: List[ContradictionResponse] = Field(default_factory=list)


class EvaluationEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    interview_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    candidate_id: uuid.UUID
    source_type: str
    source_id: Optional[uuid.UUID] = None
    competency_name: Optional[str] = None
    question_text: Optional[str] = None
    content: str
    structured_payload: Dict[str, Any]
    evidence_timestamp_seconds: float
    quality_score: float
    confidence: float
    is_candidate_evidence: bool
    is_interviewer_observation: bool
    created_at: datetime


class EvaluationReportResponse(BaseModel):
    evaluation: EvaluationResponse
    candidate_name: str
    candidate_email: Optional[str] = None
    job_title: Optional[str] = None
    interview_title: str
    evidence_items: List[EvaluationEvidenceResponse]
    generated_at: str
    is_finalized: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{interview_id}/evaluation/generate",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate evidence-grounded AI interview evaluation",
)
async def generate_evaluation(
    interview_id: uuid.UUID,
    payload: GenerateEvaluationRequest = GenerateEvaluationRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot access interview evaluation data.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    try:
        evaluation = await evaluation_service.generate_evaluation(
            interview_id=interview_id,
            workspace_id=interview.workspace_id,
            user_id=current_user.id,
            session_id=payload.session_id,
            db=db,
        )
        return EvaluationResponse.model_validate(evaluation)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get(
    "/{interview_id}/evaluation",
    response_model=EvaluationResponse,
    summary="Get current evaluation for interview",
)
async def get_evaluation(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot access interview evaluation data.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    evaluation = await evaluation_service.get_or_create_evaluation(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        candidate_id=interview.candidate_id,
        job_id=interview.job_id,
        db=db,
    )
    return EvaluationResponse.model_validate(evaluation)


@router.get(
    "/{interview_id}/evaluation/evidence",
    response_model=List[EvaluationEvidenceResponse],
    summary="Get normalized evidence records for interview",
)
async def get_evaluation_evidence(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot access interview evaluation evidence.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    evidence_list = await evidence_service.get_interview_evidence(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        db=db,
    )
    return [EvaluationEvidenceResponse.model_validate(e) for e in evidence_list]


@router.patch(
    "/{interview_id}/evaluation/competencies/{competency_score_id}",
    response_model=EvaluationResponse,
    summary="Interviewer overrides competency rubric score with audited rationale",
)
@router.put(
    "/{interview_id}/evaluation/competency-scores/{competency_score_id}/override",
    response_model=EvaluationResponse,
    summary="Interviewer overrides competency rubric score with audited rationale (PUT alias)",
)
async def override_score(
    interview_id: uuid.UUID,
    competency_score_id: uuid.UUID,
    payload: OverrideScoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role in (UserRole.CANDIDATE, "candidate") or str(getattr(current_user.role, "value", current_user.role)).lower() == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot modify evaluation scores.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    evaluation = await evaluation_service.get_or_create_evaluation(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        candidate_id=interview.candidate_id,
        job_id=interview.job_id,
        db=db,
    )

    try:
        updated_eval = await evaluation_service.override_competency_score(
            evaluation_id=evaluation.id,
            competency_score_id=competency_score_id,
            workspace_id=interview.workspace_id,
            user_id=current_user.id,
            new_rubric_level=payload.get_rubric_level(),
            rationale=payload.get_rationale(),
            db=db,
        )
        return EvaluationResponse.model_validate(updated_eval)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/{interview_id}/evaluation/approve",
    response_model=EvaluationResponse,
    summary="Interviewer approves evaluation draft",
)
async def approve_evaluation(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot approve evaluations.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    evaluation = await evaluation_service.get_or_create_evaluation(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        candidate_id=interview.candidate_id,
        job_id=interview.job_id,
        db=db,
    )

    try:
        updated = await evaluation_service.approve_evaluation(
            evaluation_id=evaluation.id,
            workspace_id=interview.workspace_id,
            user_id=current_user.id,
            db=db,
        )
        return EvaluationResponse.model_validate(updated)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/{interview_id}/evaluation/finalize",
    response_model=EvaluationResponse,
    summary="Finalize and lock evaluation into immutable state",
)
async def finalize_evaluation(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot finalize evaluations.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    evaluation = await evaluation_service.get_or_create_evaluation(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        candidate_id=interview.candidate_id,
        job_id=interview.job_id,
        db=db,
    )

    try:
        finalized = await evaluation_service.finalize_evaluation(
            evaluation_id=evaluation.id,
            workspace_id=interview.workspace_id,
            user_id=current_user.id,
            db=db,
        )
        return EvaluationResponse.model_validate(finalized)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get(
    "/{interview_id}/evaluation/report",
    response_model=EvaluationReportResponse,
    summary="Get full assembled interview evaluation report",
)
async def get_evaluation_report(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot access evaluation reports.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    try:
        report_data = await evaluation_service.get_evaluation_report(
            interview_id=interview_id,
            workspace_id=interview.workspace_id,
            db=db,
        )
        return EvaluationReportResponse(
            evaluation=EvaluationResponse.model_validate(report_data["evaluation"]),
            candidate_name=report_data["candidate_name"],
            candidate_email=report_data["candidate_email"],
            job_title=report_data["job_title"],
            interview_title=report_data["interview_title"],
            evidence_items=[EvaluationEvidenceResponse.model_validate(e) for e in report_data["evidence_items"]],
            generated_at=report_data["generated_at"],
            is_finalized=report_data["is_finalized"],
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

"""
Adaptive Interview API Endpoints — Phase 14.

REST endpoints for:
- Live Speech Transcript Segments & Response Boundary Ingestion
- Real-time AI Adaptive Recommendation Generation
- Recommendation Action Lifecycle: Accept, Edit, Reject, Skip
- Live Competency Coverage Matrix Retrieval
"""

import base64
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    verify_interview_access,
    verify_workspace_access,
)
from app.models.adaptive_interview import (
    AIInterviewRecommendation,
    RecommendationAction,
    RecommendationStatus,
    ResponseBoundaryStatus,
    TranscriptSegment,
)
from app.models.interview import Interview
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole
from app.services.adaptive_interview_service import adaptive_interview_service
from app.services.stt_service import stt_service
from app.services.transcript_service import transcript_service

logger = logging.getLogger("interviewos.api.adaptive_endpoints")

router = APIRouter(prefix="/interviews", tags=["Adaptive Interviewer"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class TranscriptSegmentCreate(BaseModel):
    speaker_role: str = Field(default="candidate", description="candidate, interviewer, system")
    speaker_name: Optional[str] = None
    text: str = Field(..., description="Transcript text content")
    start_time_seconds: float = Field(default=0.0)
    end_time_seconds: float = Field(default=0.0)
    confidence: float = Field(default=1.0)
    is_final: bool = Field(default=True)
    detected_topics: List[str] = Field(default_factory=list)


class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    speaker_role: str
    speaker_name: Optional[str] = None
    start_time_seconds: float
    end_time_seconds: float
    text: str
    confidence: float
    is_final: bool
    detected_topics: List[str]
    created_at: datetime


class TranscriptIngestResponse(BaseModel):
    segment: TranscriptSegmentResponse
    boundary_status: str
    boundary_reason: str


class AudioTranscribeRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64-encoded audio chunk (WAV, PCM, or WebM)")
    speaker_role: str = Field(default="candidate", description="candidate or interviewer")
    filename: str = Field(default="chunk.wav")
    start_time_seconds: float = Field(default=0.0)
    end_time_seconds: float = Field(default=0.0)
    is_final: bool = Field(default=True)


class GenerateRecommendationRequest(BaseModel):
    session_id: Optional[uuid.UUID] = None
    current_question: Optional[str] = None
    candidate_response: Optional[str] = None
    competency_focus: Optional[str] = None
    difficulty: str = Field(default="medium")


class EditRecommendationRequest(BaseModel):
    edited_question: str = Field(..., description="Modified question text approved by interviewer")


class RejectRecommendationRequest(BaseModel):
    reason: Optional[str] = Field(default=None, description="Optional decline explanation")


class AIRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    action: str
    status: str
    recommended_question: str
    original_question: Optional[str] = None
    edited_question: Optional[str] = None
    competency: Optional[str] = None
    difficulty: str
    reason: str
    evidence_target: Optional[str] = None
    time_cost_estimate_seconds: int
    confidence: float
    source_question_id: Optional[uuid.UUID] = None
    source_claim_id: Optional[uuid.UUID] = None
    context_revision: int
    requires_interviewer_approval: bool
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    created_at: datetime


class CompetencyEvidenceItem(BaseModel):
    id: str
    competency: str
    evidence_strength: str
    status: str
    questions_asked_count: int
    demonstrated_concepts: List[str]
    missing_concepts: List[str]
    notes: Optional[str] = None


class LiveCoverageMatrixResponse(BaseModel):
    total_competencies: int
    covered_competencies: int
    coverage_percentage: float
    competencies: List[CompetencyEvidenceItem]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{interview_id}/adaptive/transcripts",
    response_model=TranscriptIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest speech transcript segment and calculate response boundary",
)
async def ingest_transcript_segment(
    interview_id: uuid.UUID,
    payload: TranscriptSegmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    segment, boundary_status, boundary_reason = await transcript_service.add_segment(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        speaker_role=payload.speaker_role,
        text=payload.text,
        speaker_id=current_user.id,
        speaker_name=current_user.full_name,
        start_time_seconds=payload.start_time_seconds,
        end_time_seconds=payload.end_time_seconds,
        confidence=payload.confidence,
        is_final=payload.is_final,
        detected_topics=payload.detected_topics,
        db=db,
    )
    await db.commit()

    return TranscriptIngestResponse(
        segment=TranscriptSegmentResponse.model_validate(segment),
        boundary_status=boundary_status.value if hasattr(boundary_status, "value") else str(boundary_status),
        boundary_reason=boundary_reason,
    )


@router.post(
    "/{interview_id}/adaptive/audio/transcribe",
    response_model=TranscriptIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Transcribe raw audio chunk using active STT provider and compute response boundary",
)
async def transcribe_audio_chunk(
    interview_id: uuid.UUID,
    payload: AudioTranscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    try:
        audio_bytes = base64.b64decode(payload.audio_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 audio payload: {str(e)}",
        )

    if not audio_bytes or len(audio_bytes) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio chunk is empty or too small to transcribe.",
        )

    segment, boundary_status, boundary_reason = await stt_service.process_audio_chunk(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        audio_bytes=audio_bytes,
        speaker_role=payload.speaker_role,
        speaker_id=current_user.id,
        speaker_name=current_user.full_name,
        filename=payload.filename,
        start_time_seconds=payload.start_time_seconds,
        end_time_seconds=payload.end_time_seconds,
        is_final=payload.is_final,
        db=db,
    )
    await db.commit()

    return TranscriptIngestResponse(
        segment=TranscriptSegmentResponse.model_validate(segment),
        boundary_status=boundary_status.value if hasattr(boundary_status, "value") else str(boundary_status),
        boundary_reason=boundary_reason,
    )


@router.get(
    "/{interview_id}/adaptive/audio/stt/health",
    summary="Check health and capabilities of active STT provider",
)
async def get_stt_health(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    provider = stt_service.get_active_provider()
    health_info = await provider.health()
    caps = provider.capabilities()
    return {
        "health": health_info,
        "capabilities": caps,
    }


@router.get(
    "/{interview_id}/adaptive/transcripts",
    response_model=List[TranscriptSegmentResponse],
    summary="Get transcript segments for interview session",
)
async def get_transcripts(
    interview_id: uuid.UUID,
    limit: int = Query(default=100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    segments = await transcript_service.get_interview_transcripts(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        db=db,
        limit=limit,
    )
    return [TranscriptSegmentResponse.model_validate(s) for s in segments]


@router.post(
    "/{interview_id}/adaptive/recommendations/generate",
    response_model=AIRecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger real-time adaptive interview recommendation",
)
async def generate_recommendation(
    interview_id: uuid.UUID,
    payload: GenerateRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Candidate users are strictly forbidden from interviewer-facing AI recommendations
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot access adaptive interviewer recommendations.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    rec = await adaptive_interview_service.generate_recommendation(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        user_id=current_user.id,
        session_id=payload.session_id,
        current_question=payload.current_question,
        candidate_response=payload.candidate_response,
        competency_focus=payload.competency_focus,
        difficulty=payload.difficulty,
        db=db,
    )
    await db.commit()
    await db.refresh(rec)

    return AIRecommendationResponse.model_validate(rec)


@router.get(
    "/{interview_id}/adaptive/recommendations",
    response_model=List[AIRecommendationResponse],
    summary="Get recommendation history for interview",
)
async def get_recommendations(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot access adaptive interviewer recommendations.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    stmt = (
        select(AIInterviewRecommendation)
        .where(
            AIInterviewRecommendation.interview_id == interview_id,
            AIInterviewRecommendation.workspace_id == interview.workspace_id,
            AIInterviewRecommendation.is_deleted.is_(False),
        )
        .order_by(desc(AIInterviewRecommendation.created_at))
        .limit(20)
    )
    res = await db.execute(stmt)
    recs = res.scalars().all()
    return [AIRecommendationResponse.model_validate(r) for r in recs]


@router.post(
    "/{interview_id}/adaptive/recommendations/{recommendation_id}/accept",
    response_model=AIRecommendationResponse,
    summary="Interviewer accepts and asks the recommended question",
)
async def accept_recommendation(
    interview_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot modify adaptive recommendations.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    rec = await adaptive_interview_service.accept_recommendation(
        recommendation_id=recommendation_id,
        workspace_id=interview.workspace_id,
        user_id=current_user.id,
        db=db,
    )
    return AIRecommendationResponse.model_validate(rec)


@router.post(
    "/{interview_id}/adaptive/recommendations/{recommendation_id}/edit",
    response_model=AIRecommendationResponse,
    summary="Interviewer edits and accepts the recommended question",
)
async def edit_recommendation(
    interview_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    payload: EditRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot modify adaptive recommendations.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    rec = await adaptive_interview_service.edit_recommendation(
        recommendation_id=recommendation_id,
        workspace_id=interview.workspace_id,
        user_id=current_user.id,
        edited_question=payload.edited_question,
        db=db,
    )
    return AIRecommendationResponse.model_validate(rec)


@router.post(
    "/{interview_id}/adaptive/recommendations/{recommendation_id}/reject",
    response_model=AIRecommendationResponse,
    summary="Interviewer declines recommendation",
)
async def reject_recommendation(
    interview_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    payload: RejectRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot modify adaptive recommendations.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    rec = await adaptive_interview_service.reject_recommendation(
        recommendation_id=recommendation_id,
        workspace_id=interview.workspace_id,
        user_id=current_user.id,
        reason=payload.reason,
        db=db,
    )
    return AIRecommendationResponse.model_validate(rec)


@router.post(
    "/{interview_id}/adaptive/recommendations/{recommendation_id}/skip",
    response_model=AIRecommendationResponse,
    summary="Interviewer skips recommendation",
)
async def skip_recommendation(
    interview_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot modify adaptive recommendations.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    rec = await adaptive_interview_service.skip_recommendation(
        recommendation_id=recommendation_id,
        workspace_id=interview.workspace_id,
        user_id=current_user.id,
        db=db,
    )
    return AIRecommendationResponse.model_validate(rec)


@router.get(
    "/{interview_id}/adaptive/coverage",
    response_model=LiveCoverageMatrixResponse,
    summary="Get live competency coverage matrix",
)
async def get_live_coverage(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot access competency coverage metrics.",
        )

    interview = await verify_interview_access(interview_id, current_user, db)
    await verify_workspace_access(interview.workspace_id, current_user, db)

    coverage_data = await adaptive_interview_service.get_live_coverage(
        interview_id=interview_id,
        workspace_id=interview.workspace_id,
        db=db,
    )
    return LiveCoverageMatrixResponse(**coverage_data)

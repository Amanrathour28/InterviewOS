"""Phase 17 — Instant Interview & Candidate Join endpoints.

Routes:
  POST /interviews/instant         — create instant interview (auth required)
  GET  /interviews/join/{token}    — public: get interview metadata via join token
  POST /interviews/join/{token}/identity   — submit candidate identity, get session token
  GET  /interviews/join/{token}/status     — poll interview status (candidate session)
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_candidate_session, get_current_user, get_db, verify_workspace_access
from app.core.security import create_candidate_session_token, hash_token
from app.models.candidate import Candidate, CandidateSource, CandidateStatus
from app.models.interview import Interview, InterviewDifficulty, InterviewStatus, InterviewType
from app.models.scheduling import InterviewInvitation, InvitationStatus, RecipientType
from app.models.workspace import WorkspaceMembership, WorkspaceMemberRole
from app.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas (local to this module — no separate schema file needed)
# ---------------------------------------------------------------------------

class InstantInterviewRequest(BaseModel):
    workspace_id: uuid.UUID
    interview_type: InterviewType = InterviewType.TECHNICAL
    duration_minutes: int = Field(default=60, ge=15, le=480)
    candidate_name: Optional[str] = Field(default=None, max_length=150)
    candidate_email: Optional[str] = Field(default=None, max_length=255)


class InstantInterviewResponse(BaseModel):
    interview_id: uuid.UUID
    token: str
    join_url: str
    candidate_id: uuid.UUID


class PublicJoinInfoResponse(BaseModel):
    interview_id: uuid.UUID
    title: str
    interview_type: str
    duration_minutes: int
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    requires_identity: bool
    status: str


class CandidateIdentityRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    email: Optional[str] = Field(default=None, max_length=255)


class CandidateSessionResponse(BaseModel):
    candidate_session_token: str
    interview_id: uuid.UUID
    candidate_name: str
    expires_in_seconds: int = 14400  # 4 hours


class InterviewStatusResponse(BaseModel):
    interview_started: bool
    interview_status: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_join_url(token: str) -> str:
    """Build a frontend join URL.  Reads APP_URL from settings at call-time so
    we never hardcode the production domain."""
    from app.core.config import settings  # local import to avoid circular
    base = getattr(settings, "APP_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/join/{token}"


# ---------------------------------------------------------------------------
# POST /interviews/instant
# ---------------------------------------------------------------------------

@router.post(
    "/interviews/instant",
    response_model=InstantInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an Instant Interview session with a secure shareable join link",
    tags=["Instant Interview"],
)
async def create_instant_interview(
    payload: InstantInterviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstantInterviewResponse:
    """Authenticated interviewers only.

    Atomically:
    1. Validates workspace membership.
    2. Creates a guest Candidate.
    3. Creates an Interview in READY state.
    4. Creates an InterviewInvitation with a cryptographically secure token.
    5. Returns the shareable join URL (raw token is returned once and never persisted).
    """
    # 1. Workspace access check
    ws_membership = await verify_workspace_access(payload.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
        WorkspaceMemberRole.INTERVIEWER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating interviews requires Admin, Recruiter, or Interviewer workspace role",
        )

    # 2. Create guest Candidate
    candidate_first = "Guest"
    candidate_last = "Candidate"
    candidate_email_val = "guest@interviewos.local"

    if payload.candidate_name:
        parts = payload.candidate_name.strip().split(" ", 1)
        candidate_first = parts[0]
        candidate_last = parts[1] if len(parts) > 1 else "Candidate"

    if payload.candidate_email:
        candidate_email_val = payload.candidate_email.lower().strip()

    guest_candidate = Candidate(
        workspace_id=payload.workspace_id,
        created_by=current_user.id,
        first_name=candidate_first,
        last_name=candidate_last,
        email=candidate_email_val,
        status=CandidateStatus.NEW,
        source=CandidateSource.OTHER,
        is_guest=True,
    )
    db.add(guest_candidate)
    await db.flush()  # get candidate.id before interview creation

    # 3. Create Interview
    type_label_map = {
        InterviewType.TECHNICAL: "Technical Interview",
        InterviewType.CODING: "Coding Interview",
        InterviewType.SYSTEM_DESIGN: "System Design Interview",
        InterviewType.BEHAVIORAL: "Behavioral Interview",
        InterviewType.MIXED: "Mixed Interview",
        InterviewType.SCREENING: "Screening Interview",
        InterviewType.CUSTOM: "Interview",
    }
    title = type_label_map.get(payload.interview_type, "Technical Interview")
    if payload.candidate_name:
        title = f"{title} — {payload.candidate_name.strip()}"

    new_interview = Interview(
        workspace_id=payload.workspace_id,
        candidate_id=guest_candidate.id,
        created_by=current_user.id,
        title=title,
        description="Instant interview session created via quick-start.",
        interview_type=payload.interview_type,
        status=InterviewStatus.READY,  # immediately ready — no scheduling step
        difficulty=InterviewDifficulty.MID,
        duration_minutes=payload.duration_minutes,
        timezone="UTC",
    )
    db.add(new_interview)
    await db.flush()

    # 4. Generate invitation token (raw never stored)
    raw_token = secrets.token_urlsafe(32)
    token_hash = _sha256(raw_token)

    invitation = InterviewInvitation(
        interview_id=new_interview.id,
        workspace_id=payload.workspace_id,
        recipient_type=RecipientType.CANDIDATE,
        email=candidate_email_val,
        token_hash=token_hash,
        status=InvitationStatus.SENT,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        sent_at=datetime.now(timezone.utc),
        candidate_name=payload.candidate_name,
        candidate_email=payload.candidate_email,
    )
    db.add(invitation)

    await db.commit()
    await db.refresh(new_interview)

    join_url = _build_join_url(raw_token)

    return InstantInterviewResponse(
        interview_id=new_interview.id,
        token=raw_token,
        join_url=join_url,
        candidate_id=guest_candidate.id,
    )


# ---------------------------------------------------------------------------
# GET /interviews/join/{token}  — PUBLIC
# ---------------------------------------------------------------------------

@router.get(
    "/interviews/join/{token}",
    response_model=PublicJoinInfoResponse,
    summary="Get public interview metadata via secure join token",
    tags=["Candidate Join"],
)
async def get_join_info(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> PublicJoinInfoResponse:
    """Public endpoint — no authentication required.

    Validates the token and returns safe candidate-facing metadata.
    Never returns: interviewer identity, workspace details, evaluation data,
    notes, internal IDs beyond interview_id.
    """
    token_hash = _sha256(token)
    stmt = (
        select(InterviewInvitation)
        .where(InterviewInvitation.token_hash == token_hash)
        .options(
            selectinload(InterviewInvitation.interview).selectinload(Interview.candidate),
        )
    )
    res = await db.execute(stmt)
    invitation = res.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This interview link is invalid or has expired.",
        )

    # Check expiration
    now_utc = datetime.now(timezone.utc)
    exp_utc = (
        invitation.expires_at
        if invitation.expires_at.tzinfo
        else invitation.expires_at.replace(tzinfo=timezone.utc)
    )
    if exp_utc < now_utc:
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This interview link has expired.",
        )

    itw = invitation.interview
    if not itw or itw.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This interview is no longer available.",
        )

    if itw.status == InterviewStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This interview has been cancelled.",
        )

    if itw.status == InterviewStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This interview has already ended.",
        )

    # Determine whether we already know the candidate's identity
    cand = itw.candidate
    known_name = invitation.candidate_name or (
        f"{cand.first_name} {cand.last_name}"
        if cand and not cand.is_guest
        else None
    )
    known_email = invitation.candidate_email or (
        cand.email if cand and not cand.is_guest else None
    )

    requires_identity = not bool(invitation.candidate_name) and (
        not cand or cand.is_guest
    )

    return PublicJoinInfoResponse(
        interview_id=itw.id,
        title=itw.title,
        interview_type=itw.interview_type.value,
        duration_minutes=itw.duration_minutes,
        candidate_name=known_name,
        candidate_email=known_email,
        requires_identity=requires_identity,
        status=itw.status.value,
    )


# ---------------------------------------------------------------------------
# POST /interviews/join/{token}/identity  — PUBLIC
# ---------------------------------------------------------------------------

@router.post(
    "/interviews/join/{token}/identity",
    response_model=CandidateSessionResponse,
    summary="Submit candidate identity and receive a scoped session token",
    tags=["Candidate Join"],
)
async def submit_candidate_identity(
    token: str,
    payload: CandidateIdentityRequest,
    db: AsyncSession = Depends(get_db),
) -> CandidateSessionResponse:
    """Public endpoint — no platform auth required.

    After validating the join token, the candidate provides their name/email.
    The guest Candidate record is updated and a short-lived candidate session
    JWT is issued (4 hour expiry, scope=candidate).

    The raw session token is returned to the client.
    Only its SHA-256 hash is persisted in `invitation.candidate_session_token_hash`.
    """
    token_hash = _sha256(token)
    stmt = (
        select(InterviewInvitation)
        .where(InterviewInvitation.token_hash == token_hash)
        .options(
            selectinload(InterviewInvitation.interview).selectinload(Interview.candidate),
        )
    )
    res = await db.execute(stmt)
    invitation = res.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This interview link is invalid or has expired.",
        )

    now_utc = datetime.now(timezone.utc)
    exp_utc = (
        invitation.expires_at
        if invitation.expires_at.tzinfo
        else invitation.expires_at.replace(tzinfo=timezone.utc)
    )
    if exp_utc < now_utc or invitation.status == InvitationStatus.EXPIRED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This interview link has expired.",
        )

    itw = invitation.interview
    if not itw or itw.is_deleted or itw.status in [
        InterviewStatus.CANCELLED,
        InterviewStatus.COMPLETED,
    ]:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This interview is no longer available.",
        )

    # Update guest candidate identity
    cand = itw.candidate
    name_parts = payload.name.strip().split(" ", 1)
    if cand and cand.is_guest:
        cand.first_name = name_parts[0]
        cand.last_name = name_parts[1] if len(name_parts) > 1 else "Candidate"
        if payload.email:
            cand.email = payload.email.lower().strip()

    # Update invitation identity
    invitation.candidate_name = payload.name.strip()
    if payload.email:
        invitation.candidate_email = payload.email.lower().strip()

    # Mark invitation as accepted
    if invitation.status == InvitationStatus.SENT:
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = now_utc

    # Issue candidate session JWT
    session_token = create_candidate_session_token(
        invitation_id=str(invitation.id),
        interview_id=str(itw.id),
        candidate_name=payload.name.strip(),
    )

    # Persist only the hash
    session_token_hash = _sha256(session_token)
    invitation.candidate_session_token_hash = session_token_hash

    await db.commit()

    return CandidateSessionResponse(
        candidate_session_token=session_token,
        interview_id=itw.id,
        candidate_name=payload.name.strip(),
        expires_in_seconds=14400,
    )


# ---------------------------------------------------------------------------
# GET /interviews/join/{token}/status  — candidate session protected
# ---------------------------------------------------------------------------

@router.get(
    "/interviews/join/{token}/status",
    response_model=InterviewStatusResponse,
    summary="Poll interview status (candidate waiting room)",
    tags=["Candidate Join"],
)
async def get_join_status(
    token: str,
    candidate_claims: Dict[str, Any] = Depends(get_candidate_session),
    db: AsyncSession = Depends(get_db),
) -> InterviewStatusResponse:
    """Candidate-session protected.

    Used by the waiting room to poll whether the interviewer has started.
    Returns only interview status — never private interview data.
    """
    # Validate token → interview_id match from JWT claims
    token_hash = _sha256(token)
    stmt = select(InterviewInvitation).where(InterviewInvitation.token_hash == token_hash)
    res = await db.execute(stmt)
    invitation = res.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )

    # Verify the candidate session's interview_id matches this invitation's interview
    claimed_interview_id = candidate_claims.get("interview_id")
    if str(invitation.interview_id) != claimed_interview_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this interview.",
        )

    itw_stmt = select(Interview).where(Interview.id == invitation.interview_id)
    itw = (await db.execute(itw_stmt)).scalar_one_or_none()

    if not itw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

    started = itw.status == InterviewStatus.IN_PROGRESS

    return InterviewStatusResponse(
        interview_started=started,
        interview_status=itw.status.value,
    )

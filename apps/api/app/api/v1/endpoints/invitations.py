import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, verify_interview_access, verify_workspace_access
from app.models.interview import Interview
from app.models.scheduling import InterviewInvitation
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole
from app.schemas.scheduling import (
    InvitationActionRequest,
    InvitationCreate,
    InvitationResponse,
    PublicInvitationDetail,
)
from app.services.invitation_service import invitation_service

router = APIRouter()


@router.post(
    "/interviews/{interview_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and dispatch an interview invitation",
)
async def create_invitation(
    payload: InvitationCreate,
    interview: Interview = Depends(verify_interview_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_membership = await verify_workspace_access(interview.workspace_id, current_user, db)
    if ws_membership and ws_membership.role not in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
        WorkspaceMemberRole.INTERVIEWER,
    ] and current_user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to send interview invitations",
        )

    invitation, raw_token = await invitation_service.create_invitation(
        interview_id=interview.id,
        workspace_id=interview.workspace_id,
        email=payload.email,
        recipient_type=payload.recipient_type,
        recipient_user_id=payload.recipient_user_id,
        recipient_candidate_id=payload.recipient_candidate_id,
        db=db,
    )

    return InvitationResponse(
        id=invitation.id,
        interview_id=invitation.interview_id,
        workspace_id=invitation.workspace_id,
        recipient_type=invitation.recipient_type,
        email=invitation.email,
        status=invitation.status,
        expires_at=invitation.expires_at,
        sent_at=invitation.sent_at,
        accepted_at=invitation.accepted_at,
        declined_at=invitation.declined_at,
        created_at=invitation.created_at,
    )


@router.get(
    "/interviews/{interview_id}/invitations",
    response_model=List[InvitationResponse],
    summary="List all sent invitations for an interview",
)
async def list_interview_invitations(
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterviewInvitation)
        .where(InterviewInvitation.interview_id == interview.id)
        .order_by(InterviewInvitation.created_at.desc())
    )
    res = await db.execute(stmt)
    invitations = res.scalars().all()

    return [
        InvitationResponse(
            id=inv.id,
            interview_id=inv.interview_id,
            workspace_id=inv.workspace_id,
            recipient_type=inv.recipient_type,
            email=inv.email,
            status=inv.status,
            expires_at=inv.expires_at,
            sent_at=inv.sent_at,
            accepted_at=inv.accepted_at,
            declined_at=inv.declined_at,
            created_at=inv.created_at,
        )
        for inv in invitations
    ]


# --- PUBLIC INVITATION ENDPOINTS (NO AUTH REQUIRED) ---

@router.get(
    "/invitations/{token}",
    response_model=PublicInvitationDetail,
    summary="Inspect public invitation details via secure token",
)
async def get_public_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    return await invitation_service.get_public_invitation_detail(token, db)


@router.post(
    "/invitations/{token}/accept",
    response_model=InvitationResponse,
    summary="Accept an interview invitation",
)
async def accept_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    invitation = await invitation_service.accept_invitation(token, db)
    return InvitationResponse(
        id=invitation.id,
        interview_id=invitation.interview_id,
        workspace_id=invitation.workspace_id,
        recipient_type=invitation.recipient_type,
        email=invitation.email,
        status=invitation.status,
        expires_at=invitation.expires_at,
        sent_at=invitation.sent_at,
        accepted_at=invitation.accepted_at,
        declined_at=invitation.declined_at,
        created_at=invitation.created_at,
    )


@router.post(
    "/invitations/{token}/decline",
    response_model=InvitationResponse,
    summary="Decline an interview invitation",
)
async def decline_invitation(
    token: str,
    payload: Optional[InvitationActionRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    reason = payload.reason if payload else None
    invitation = await invitation_service.decline_invitation(token, db, reason=reason)
    return InvitationResponse(
        id=invitation.id,
        interview_id=invitation.interview_id,
        workspace_id=invitation.workspace_id,
        recipient_type=invitation.recipient_type,
        email=invitation.email,
        status=invitation.status,
        expires_at=invitation.expires_at,
        sent_at=invitation.sent_at,
        accepted_at=invitation.accepted_at,
        declined_at=invitation.declined_at,
        created_at=invitation.created_at,
    )

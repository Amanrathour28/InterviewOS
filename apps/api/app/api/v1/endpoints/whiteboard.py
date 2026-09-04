import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user, get_optional_current_user
from app.models.user import User, UserRole
from app.models.session import InterviewSession
from app.models.interview import Interview, InterviewParticipant, ParticipantRole
from app.schemas.whiteboard import (
    WhiteboardResponse,
    WhiteboardUpdateRequest,
    WhiteboardLockRequest,
    WhiteboardSnapshotCreateRequest,
    WhiteboardSnapshotResponse,
)
from app.services.whiteboard_service import whiteboard_service

router = APIRouter()


async def _check_session_participant_role(
    db: AsyncSession,
    session_id: uuid.UUID,
    user: Optional[User],
) -> bool:
    """Returns True if the user is a candidate, False if interviewer/host."""
    if not user:
        return True  # Anonymous or candidate token default

    if user.role in (UserRole.PLATFORM_ADMIN, UserRole.ORGANIZATION_ADMIN, UserRole.INTERVIEWER, UserRole.RECRUITER):
        return False

    # Check session creator
    sess_res = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    sess = sess_res.scalars().first()
    if sess and sess.created_by == user.id:
        return False

    return True


@router.get("/sessions/{session_id}/whiteboard", response_model=WhiteboardResponse)
async def get_session_whiteboard(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    is_candidate = await _check_session_participant_role(db, session_id, current_user)
    user_id = current_user.id if current_user else None
    return await whiteboard_service.get_or_create_whiteboard(
        db=db,
        session_id=session_id,
        user_id=user_id,
        is_candidate=is_candidate,
    )


@router.get("/whiteboards/{whiteboard_id}", response_model=WhiteboardResponse)
async def get_whiteboard(
    whiteboard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    wb = await whiteboard_service.get_whiteboard_by_id(
        db=db, whiteboard_id=whiteboard_id, is_candidate=False
    )
    is_candidate = await _check_session_participant_role(
        db, wb.interview_session_id, current_user
    )
    return await whiteboard_service.get_whiteboard_by_id(
        db=db, whiteboard_id=whiteboard_id, is_candidate=is_candidate
    )


@router.patch("/whiteboards/{whiteboard_id}", response_model=WhiteboardResponse)
async def update_whiteboard(
    whiteboard_id: uuid.UUID,
    req: WhiteboardUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    wb = await whiteboard_service.get_whiteboard_by_id(
        db=db, whiteboard_id=whiteboard_id, is_candidate=False
    )
    is_candidate = await _check_session_participant_role(
        db, wb.interview_session_id, current_user
    )
    user_id = current_user.id if current_user else None
    return await whiteboard_service.update_whiteboard(
        db=db,
        whiteboard_id=whiteboard_id,
        req=req,
        user_id=user_id,
        is_candidate=is_candidate,
    )


@router.post("/whiteboards/{whiteboard_id}/lock", response_model=WhiteboardResponse)
async def set_whiteboard_lock(
    whiteboard_id: uuid.UUID,
    req: WhiteboardLockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    wb = await whiteboard_service.get_whiteboard_by_id(
        db=db, whiteboard_id=whiteboard_id, is_candidate=False
    )
    is_candidate = await _check_session_participant_role(
        db, wb.interview_session_id, current_user
    )
    if is_candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot toggle whiteboard lock state",
        )
    user_id = current_user.id if current_user else None
    return await whiteboard_service.set_lock_status(
        db=db,
        whiteboard_id=whiteboard_id,
        is_locked=req.is_locked,
        user_id=user_id,
    )


@router.post("/whiteboards/{whiteboard_id}/clear", response_model=WhiteboardResponse)
async def clear_whiteboard(
    whiteboard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    wb = await whiteboard_service.get_whiteboard_by_id(
        db=db, whiteboard_id=whiteboard_id, is_candidate=False
    )
    is_candidate = await _check_session_participant_role(
        db, wb.interview_session_id, current_user
    )
    if is_candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot clear the whiteboard",
        )
    user_id = current_user.id if current_user else None
    return await whiteboard_service.clear_whiteboard(
        db=db, whiteboard_id=whiteboard_id, user_id=user_id
    )


@router.post(
    "/whiteboards/{whiteboard_id}/snapshots",
    response_model=WhiteboardSnapshotResponse,
)
async def create_whiteboard_snapshot(
    whiteboard_id: uuid.UUID,
    req: WhiteboardSnapshotCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    wb = await whiteboard_service.get_whiteboard_by_id(
        db=db, whiteboard_id=whiteboard_id, is_candidate=False
    )
    is_candidate = await _check_session_participant_role(
        db, wb.interview_session_id, current_user
    )
    if is_candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot create snapshots",
        )
    user_id = current_user.id if current_user else None
    return await whiteboard_service.create_snapshot(
        db=db,
        whiteboard_id=whiteboard_id,
        label=req.label or "Milestone Checkpoint",
        source=req.source or "manual",
        user_id=user_id,
    )


@router.get(
    "/whiteboards/{whiteboard_id}/snapshots",
    response_model=List[WhiteboardSnapshotResponse],
)
async def list_whiteboard_snapshots(
    whiteboard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    wb = await whiteboard_service.get_whiteboard_by_id(
        db=db, whiteboard_id=whiteboard_id, is_candidate=False
    )
    is_candidate = await _check_session_participant_role(
        db, wb.interview_session_id, current_user
    )
    return await whiteboard_service.list_snapshots(
        db=db, whiteboard_id=whiteboard_id, is_candidate=is_candidate
    )


@router.post(
    "/whiteboards/{whiteboard_id}/snapshots/{snapshot_id}/restore",
    response_model=WhiteboardResponse,
)
async def restore_whiteboard_snapshot(
    whiteboard_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    wb = await whiteboard_service.get_whiteboard_by_id(
        db=db, whiteboard_id=whiteboard_id, is_candidate=False
    )
    is_candidate = await _check_session_participant_role(
        db, wb.interview_session_id, current_user
    )
    if is_candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidates cannot restore snapshots",
        )
    user_id = current_user.id if current_user else None
    return await whiteboard_service.restore_snapshot(
        db=db,
        whiteboard_id=whiteboard_id,
        snapshot_id=snapshot_id,
        user_id=user_id,
    )

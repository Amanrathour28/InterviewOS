import uuid
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.deps import (
    get_current_user,
    get_db,
    verify_interview_access,
    verify_workspace_access,
)
from app.models.interview import Interview, InterviewParticipant
from app.models.session import InterviewEvent, InterviewSession, NoteCategory, SessionStatus
from app.models.user import User, UserRole
from app.models.workspace import WorkspaceMemberRole
from app.schemas.session import (
    CandidateWaitingRoomResponse,
    EventResponse,
    InterviewerNoteCreate,
    InterviewerNoteResponse,
    JoinTokenResponse,
    RoomStateResponse,
    SessionActionRequest,
    SessionDetailResponse,
    SessionHealthResponse,
    SessionParticipant,
    SessionResponse,
    SessionTimelineItemResponse,
    StageChangeRequest,
)
from app.services.session_service import session_service

router = APIRouter()


async def check_session_permission(
    session: InterviewSession,
    user: User,
    db: AsyncSession,
    require_interviewer: bool = False,
) -> Tuple[bool, str]:
    """Validates session access and resolves whether user is an interviewer or candidate."""
    # Check platform admin bypass
    if user.role == "platform_admin":
        return True, "platform_admin"

    # 1. Check if user is the candidate of this interview
    is_candidate = False
    if session.interview and session.interview.candidate:
        if session.interview.candidate.email.lower() == user.email.lower():
            is_candidate = True

    # 2. Check if user is a configured panel member
    is_panelist = False
    panel_role = "interviewer"
    if session.interview and session.interview.participants:
        for p in session.interview.participants:
            if p.user_id == user.id:
                is_panelist = True
                panel_role = p.participant_role.value
                break

    # 3. Check workspace membership if not already candidate or panelist
    ws_member = None
    if not is_candidate and not is_panelist:
        ws_member = await verify_workspace_access(session.workspace_id, user, db)

    is_interviewer = is_panelist or (ws_member is not None and ws_member.role in [
        WorkspaceMemberRole.ADMIN,
        WorkspaceMemberRole.RECRUITER,
        WorkspaceMemberRole.INTERVIEWER,
    ])

    resolved_role = panel_role if is_panelist else (
        "interviewer" if is_interviewer else "candidate"
    )

    if require_interviewer and not is_interviewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Interviewer privileges required for this action",
        )

    return is_interviewer, resolved_role


@router.post(
    "/interviews/{interview_id}/session",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or retrieve the live session for an interview",
)
async def create_or_get_session(
    interview: Interview = Depends(verify_interview_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_or_create_session(
        interview=interview,
        workspace_id=interview.workspace_id,
        user_id=current_user.id,
        db=db,
    )
    return session


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get interview session details, participants, and server timestamps",
)
async def get_session_detail(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    is_interviewer, _ = await check_session_permission(session, current_user, db, require_interviewer=False)

    itw = session.interview
    participants_list: List[SessionParticipant] = []
    if itw and itw.participants:
        for p in itw.participants:
            if p.user:
                participants_list.append(
                    SessionParticipant(
                        user_id=p.user.id,
                        name=f"{p.user.first_name} {p.user.last_name}".strip(),
                        email=p.user.email,
                        role=p.participant_role.value,
                        is_primary=p.is_primary,
                        is_online=True,
                    )
                )

    cand_name = f"{itw.candidate.first_name} {itw.candidate.last_name}".strip() if itw and itw.candidate else None
    cand_email = itw.candidate.email if itw and itw.candidate else None
    job_title = itw.job.title if itw and itw.job else None
    duration_minutes = itw.duration_minutes if itw else 60

    elapsed = session_service.calculate_elapsed_seconds(session)
    remaining = session_service.calculate_remaining_seconds(session, duration_minutes)
    stage_elapsed = session_service.calculate_stage_elapsed_seconds(session)

    return SessionDetailResponse(
        id=session.id,
        interview_id=session.interview_id,
        workspace_id=session.workspace_id,
        status=session.status,
        current_stage=session.current_stage,
        stage_started_at=session.stage_started_at,
        started_at=session.started_at,
        ended_at=session.ended_at,
        paused_at=session.paused_at,
        total_paused_seconds=session.total_paused_seconds,
        last_event_sequence=session.last_event_sequence,
        created_by=session.created_by,
        created_at=session.created_at,
        updated_at=session.updated_at,
        interview_title=itw.title if itw else "Technical Interview",
        candidate_id=itw.candidate_id if itw else uuid.uuid4(),
        candidate_name=cand_name,
        candidate_email=cand_email,
        job_id=itw.job_id if itw else None,
        job_title=job_title,
        duration_minutes=duration_minutes,
        current_elapsed_seconds=elapsed,
        remaining_seconds=remaining,
        stage_elapsed_seconds=stage_elapsed,
        is_paused=(session.status == SessionStatus.PAUSED),
        is_interviewer=is_interviewer,
        participants=participants_list,
    )


@router.get(
    "/sessions/{session_id}/waiting-room",
    response_model=CandidateWaitingRoomResponse,
    summary="Get candidate-facing sanitized interview and device check details",
)
async def get_candidate_waiting_room(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=False)

    itw = session.interview
    cand_name = f"{itw.candidate.first_name} {itw.candidate.last_name}".strip() if itw and itw.candidate else current_user.first_name

    return CandidateWaitingRoomResponse(
        session_id=session.id,
        interview_id=session.interview_id,
        interview_title=itw.title if itw else "Technical Interview",
        workspace_name=session.workspace.name if session.workspace else "InterviewOS",
        scheduled_at=itw.created_at if itw else None,
        duration_minutes=itw.duration_minutes if itw else 60,
        instructions=itw.description,
        status=session.status,
        candidate_name=cand_name,
        ice_servers=session_service.get_ice_servers(),
    )


@router.post(
    "/sessions/{session_id}/start",
    response_model=SessionResponse,
    summary="Start or activate the interview session (Interviewer only)",
)
async def start_session(
    session_id: uuid.UUID,
    payload: Optional[SessionActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    return await session_service.start_session(session_id, current_user.id, db)


@router.post(
    "/sessions/{session_id}/pause",
    response_model=SessionResponse,
    summary="Pause active interview session (Interviewer only)",
)
async def pause_session(
    session_id: uuid.UUID,
    payload: Optional[SessionActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    reason = payload.reason if payload else None
    return await session_service.pause_session(session_id, current_user.id, db, reason=reason)


@router.post(
    "/sessions/{session_id}/resume",
    response_model=SessionResponse,
    summary="Resume paused interview session (Interviewer only)",
)
async def resume_session(
    session_id: uuid.UUID,
    payload: Optional[SessionActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    return await session_service.resume_session(session_id, current_user.id, db)


@router.post(
    "/sessions/{session_id}/end",
    response_model=SessionResponse,
    summary="Complete and end interview session (Interviewer only)",
)
async def end_session(
    session_id: uuid.UUID,
    payload: Optional[SessionActionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    reason = payload.reason if payload else None
    return await session_service.end_session(session_id, current_user.id, db, reason=reason)


@router.post(
    "/sessions/{session_id}/stage",
    response_model=SessionResponse,
    summary="Change interview stage sequence (Interviewer only)",
)
async def change_stage(
    session_id: uuid.UUID,
    payload: StageChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    return await session_service.change_stage(
        session_id=session_id,
        new_stage=payload.stage,
        user_id=current_user.id,
        db=db,
        reason=payload.reason,
    )


# --- INTERVIEWER STRUCTURED NOTES ---

@router.get(
    "/sessions/{session_id}/notes",
    response_model=List[InterviewerNoteResponse],
    summary="List private notes for the interview session (Interviewer only)",
)
async def list_interviewer_notes(
    session_id: uuid.UUID,
    category: Optional[NoteCategory] = Query(None),
    stage: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    notes = await session_service.list_notes(session_id, category, stage, db)
    return [
        InterviewerNoteResponse(
            id=n.id,
            session_id=n.session_id,
            user_id=n.user_id,
            author_name=f"{n.user.first_name} {n.user.last_name}".strip() if n.user else None,
            category=n.category,
            stage=n.stage,
            content=n.content,
            rating=n.rating,
            tags=n.tags or [],
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in notes
    ]


@router.post(
    "/sessions/{session_id}/notes",
    response_model=InterviewerNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a private note to the interview session (Interviewer only)",
)
async def create_interviewer_note(
    session_id: uuid.UUID,
    payload: InterviewerNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    note = await session_service.create_note(
        session_id=session_id,
        user_id=current_user.id,
        category=payload.category,
        content=payload.content,
        stage=payload.stage,
        rating=payload.rating,
        tags=payload.tags,
        db=db,
    )
    return InterviewerNoteResponse(
        id=note.id,
        session_id=note.session_id,
        user_id=note.user_id,
        author_name=f"{current_user.first_name} {current_user.last_name}".strip(),
        category=note.category,
        stage=note.stage,
        content=note.content,
        rating=note.rating,
        tags=note.tags or [],
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete(
    "/sessions/{session_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a private note (Interviewer only)",
)
async def delete_interviewer_note(
    session_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    await session_service.delete_note(session_id, note_id, current_user.id, db)


# --- LIVE ACTIVITY TIMELINE & HEALTH ---

@router.get(
    "/sessions/{session_id}/timeline",
    response_model=List[SessionTimelineItemResponse],
    summary="Get structured session activity timeline with category filtering (Interviewer only)",
)
async def get_session_timeline(
    session_id: uuid.UUID,
    category: Optional[str] = Query(None, description="Filter: all, lifecycle, stages, coding, whiteboard, chat, participants"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=True)
    items = await session_service.get_timeline(session_id, category, db)
    return [SessionTimelineItemResponse(**item) for item in items]


@router.get(
    "/sessions/{session_id}/health",
    response_model=SessionHealthResponse,
    summary="Get real-time session health diagnostics",
)
async def get_session_health(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=False)

    warnings = []
    if session.status == SessionStatus.PAUSED:
        warnings.append("Session is currently paused by the interviewer")

    return SessionHealthResponse(
        session_id=session.id,
        status=session.status,
        is_operational=(session.status in [SessionStatus.ACTIVE, SessionStatus.WAITING, SessionStatus.PAUSED]),
        active_participants_count=len(session.interview.participants) if session.interview else 1,
        websocket_healthy=True,
        webrtc_healthy=True,
        system_warnings=warnings,
    )


@router.get(
    "/sessions/{session_id}/events",
    response_model=List[EventResponse],
    summary="Retrieve session event log with sequence filtering",
)
async def get_session_events(
    session_id: uuid.UUID,
    after_sequence: Optional[int] = Query(None, description="Only fetch events with sequence > after_sequence"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    await check_session_permission(session, current_user, db, require_interviewer=False)

    query = (
        select(InterviewEvent)
        .where(InterviewEvent.session_id == session_id)
        .order_by(InterviewEvent.sequence.asc())
        .limit(limit)
    )
    if after_sequence is not None:
        query = query.where(InterviewEvent.sequence > after_sequence)

    res = await db.execute(query)
    events = res.scalars().all()
    return events


@router.post(
    "/sessions/{session_id}/join-token",
    response_model=JoinTokenResponse,
    summary="Generate secure short-lived WebSocket gateway join token",
)
async def get_join_token(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await session_service.get_session(session_id, db)
    is_interviewer, resolved_role = await check_session_permission(
        session, current_user, db, require_interviewer=False
    )

    token, expires_in = session_service.generate_join_token(
        session=session,
        user=current_user,
        role=resolved_role,
        is_interviewer=is_interviewer,
    )

    realtime_url = getattr(settings, "REALTIME_URL", "")
    if getattr(settings, "APP_ENV", "development") == "production" and ("localhost" in realtime_url or "127.0.0.1" in realtime_url):
        realtime_url = ""
    ice_servers = session_service.get_ice_servers()

    return JoinTokenResponse(
        token=token,
        session_id=session.id,
        room_id=f"interview:{session.id}",
        role=resolved_role,
        user_id=current_user.id,
        user_name=f"{current_user.first_name} {current_user.last_name}".strip(),
        is_interviewer=is_interviewer,
        expires_in_seconds=expires_in,
        realtime_url=realtime_url,
        ice_servers=ice_servers,
    )

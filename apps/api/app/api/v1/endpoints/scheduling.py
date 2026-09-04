import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_user,
    get_db,
    verify_interview_access,
    verify_workspace_access,
)
from app.models.interview import Interview
from app.models.scheduling import InterviewSchedule, ScheduleStatus
from app.models.user import User
from app.models.workspace import WorkspaceMemberRole
from app.schemas.scheduling import (
    AvailableSlotsResponse,
    ScheduleCancel,
    ScheduleCreate,
    ScheduleHistoryResponse,
    ScheduleReschedule,
    ScheduleResponse,
)
from app.services.scheduling_service import scheduling_service

router = APIRouter()


@router.post(
    "/{interview_id}/schedule",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a prepared interview configuration",
)
async def schedule_interview(
    payload: ScheduleCreate,
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
            detail="Permission denied to schedule interviews in this workspace",
        )

    schedule = await scheduling_service.schedule_interview(
        interview=interview,
        scheduled_start_at=payload.scheduled_start_at,
        timezone_str=payload.timezone,
        user_id=current_user.id,
        db=db,
    )

    return ScheduleResponse(
        id=schedule.id,
        interview_id=schedule.interview_id,
        workspace_id=schedule.workspace_id,
        scheduled_start_at=schedule.scheduled_start_at,
        scheduled_end_at=schedule.scheduled_end_at,
        timezone=schedule.timezone,
        status=schedule.status,
        created_by=schedule.created_by,
        cancelled_at=schedule.cancelled_at,
        cancelled_by=schedule.cancelled_by,
        cancellation_reason=schedule.cancellation_reason,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        history=[],
    )


@router.get(
    "/{interview_id}/schedule",
    response_model=ScheduleResponse,
    summary="Get active schedule and change history for an interview",
)
async def get_interview_schedule(
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterviewSchedule)
        .where(
            InterviewSchedule.interview_id == interview.id,
            InterviewSchedule.is_deleted.is_(False),
        )
        .order_by(InterviewSchedule.created_at.desc())
        .options(selectinload(InterviewSchedule.history))
    )
    schedule = (await db.execute(stmt)).scalars().first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No schedule found for this interview")

    history_entries = [
        ScheduleHistoryResponse(
            id=h.id,
            schedule_id=h.schedule_id,
            previous_start_at=h.previous_start_at,
            previous_end_at=h.previous_end_at,
            previous_timezone=h.previous_timezone,
            new_start_at=h.new_start_at,
            new_end_at=h.new_end_at,
            new_timezone=h.new_timezone,
            changed_by=h.changed_by,
            reason=h.reason,
            created_at=h.created_at,
        )
        for h in schedule.history
    ]

    return ScheduleResponse(
        id=schedule.id,
        interview_id=schedule.interview_id,
        workspace_id=schedule.workspace_id,
        scheduled_start_at=schedule.scheduled_start_at,
        scheduled_end_at=schedule.scheduled_end_at,
        timezone=schedule.timezone,
        status=schedule.status,
        created_by=schedule.created_by,
        cancelled_at=schedule.cancelled_at,
        cancelled_by=schedule.cancelled_by,
        cancellation_reason=schedule.cancellation_reason,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        history=history_entries,
    )


@router.patch(
    "/{interview_id}/schedule",
    response_model=ScheduleResponse,
    summary="Reschedule an interview with conflict checking",
)
async def reschedule_interview(
    payload: ScheduleReschedule,
    interview: Interview = Depends(verify_interview_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewSchedule).where(
        InterviewSchedule.interview_id == interview.id,
        InterviewSchedule.status.in_([ScheduleStatus.CONFIRMED, ScheduleStatus.PENDING]),
        InterviewSchedule.is_deleted.is_(False),
    )
    schedule = (await db.execute(stmt)).scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active schedule to reschedule")

    updated_schedule = await scheduling_service.reschedule_interview(
        schedule_id=schedule.id,
        new_start_at=payload.scheduled_start_at,
        new_timezone_str=payload.timezone,
        user_id=current_user.id,
        db=db,
        reason=payload.reason,
    )

    return await get_interview_schedule(interview, db)


@router.delete(
    "/{interview_id}/schedule",
    response_model=ScheduleResponse,
    summary="Cancel scheduled interview",
)
async def cancel_interview_schedule(
    payload: Optional[ScheduleCancel] = None,
    interview: Interview = Depends(verify_interview_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewSchedule).where(
        InterviewSchedule.interview_id == interview.id,
        InterviewSchedule.status.in_([ScheduleStatus.CONFIRMED, ScheduleStatus.PENDING]),
        InterviewSchedule.is_deleted.is_(False),
    )
    schedule = (await db.execute(stmt)).scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active schedule found to cancel")

    reason = payload.cancellation_reason if payload else "Cancelled by organizer"
    cancelled_schedule = await scheduling_service.cancel_schedule(
        schedule_id=schedule.id,
        user_id=current_user.id,
        cancellation_reason=reason,
        db=db,
    )

    return await get_interview_schedule(interview, db)


@router.get(
    "/{interview_id}/available-slots",
    response_model=AvailableSlotsResponse,
    summary="Generate candidate-compatible available slots for an interview",
)
async def get_available_slots(
    date_str: str = Query(..., description="Target date in YYYY-MM-DD format", alias="date"),
    timezone_str: str = Query("UTC", description="Target IANA timezone", alias="timezone"),
    interview: Interview = Depends(verify_interview_access),
    db: AsyncSession = Depends(get_db),
):
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")

    return await scheduling_service.generate_available_slots(
        interview=interview,
        target_date=target_date,
        timezone_str=timezone_str,
        db=db,
    )

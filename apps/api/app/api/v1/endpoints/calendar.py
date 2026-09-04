import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, verify_workspace_access
from app.models.interview import Interview, InterviewParticipant
from app.models.scheduling import InterviewSchedule, ScheduleStatus
from app.models.user import User
from app.schemas.scheduling import CalendarEvent

router = APIRouter()


@router.get(
    "/events",
    response_model=List[CalendarEvent],
    summary="List scheduled interview events for a workspace calendar within a date range",
)
async def get_calendar_events(
    workspace_id: uuid.UUID = Query(..., description="Target workspace ID"),
    start_date: Optional[datetime] = Query(None, description="Start date (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date (UTC)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user, db)

    query = (
        select(InterviewSchedule)
        .where(
            InterviewSchedule.workspace_id == workspace_id,
            InterviewSchedule.is_deleted.is_(False),
        )
        .options(
            selectinload(InterviewSchedule.interview).selectinload(Interview.candidate),
            selectinload(InterviewSchedule.interview).selectinload(Interview.job),
            selectinload(InterviewSchedule.interview).selectinload(Interview.participants),
        )
        .order_by(InterviewSchedule.scheduled_start_at.asc())
    )

    if start_date:
        query = query.where(InterviewSchedule.scheduled_end_at >= start_date)
    if end_date:
        query = query.where(InterviewSchedule.scheduled_start_at <= end_date)

    res = await db.execute(query)
    schedules = res.scalars().all()

    events: List[CalendarEvent] = []
    for s in schedules:
        itw = s.interview
        if not itw or itw.is_deleted:
            continue

        cand_name = f"{itw.candidate.first_name} {itw.candidate.last_name}" if itw.candidate else None
        cand_email = itw.candidate.email if itw.candidate else None
        job_title = itw.job.title if itw.job else None

        events.append(
            CalendarEvent(
                id=s.id,
                interview_id=itw.id,
                workspace_id=s.workspace_id,
                title=itw.title,
                candidate_id=itw.candidate_id,
                candidate_name=cand_name,
                candidate_email=cand_email,
                job_id=itw.job_id,
                job_title=job_title,
                scheduled_start_at=s.scheduled_start_at,
                scheduled_end_at=s.scheduled_end_at,
                timezone=s.timezone,
                status=s.status,
                interview_status=itw.status.value,
                interview_type=itw.interview_type.value,
                duration_minutes=itw.duration_minutes,
                participant_count=len(itw.participants),
            )
        )

    return events

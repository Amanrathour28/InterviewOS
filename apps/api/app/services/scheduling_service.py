import logging
import uuid
import zoneinfo
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.interview import Interview, InterviewParticipant, InterviewStatus
from app.models.scheduling import (
    AvailabilityException,
    InterviewSchedule,
    InterviewScheduleHistory,
    Notification,
    NotificationType,
    ScheduleStatus,
    UserAvailability,
)
from app.models.user import User
from app.schemas.scheduling import AvailableSlot, AvailableSlotsResponse
from app.services.email_service import email_service
from app.services.interview_service import interview_service

logger = logging.getLogger(__name__)


class SchedulingService:
    """Enterprise scheduling engine with interval overlap detection, timezone handling, and slot generation."""

    def validate_timezone(self, tz_str: str) -> zoneinfo.ZoneInfo:
        """Validates that a timezone identifier is supported by the IANA database."""
        if not tz_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timezone identifier is required",
            )
        try:
            return zoneinfo.ZoneInfo(tz_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid IANA timezone identifier: '{tz_str}'. Examples: 'UTC', 'Asia/Kolkata', 'America/New_York'",
            )

    def canonicalize_datetimes(
        self,
        start_dt: datetime,
        tz_name: str,
        duration_minutes: int,
        allow_past: bool = False,
    ) -> Tuple[datetime, datetime]:
        """Converts an input datetime into a canonical UTC start and calculates canonical end time."""
        zi = self.validate_timezone(tz_name)

        # 1. Attach timezone if naive or convert to target timezone
        if start_dt.tzinfo is None:
            local_dt = start_dt.replace(tzinfo=zi)
        else:
            local_dt = start_dt.astimezone(zi)

        # 2. Canonical UTC conversion
        start_utc = local_dt.astimezone(timezone.utc)

        # 3. Validation
        if not allow_past:
            now_utc = datetime.now(timezone.utc)
            if start_utc < (now_utc - timedelta(minutes=5)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot schedule interviews in the past.",
                )

        if duration_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview duration must be greater than zero.",
            )

        end_utc = start_utc + timedelta(minutes=duration_minutes)
        return start_utc, end_utc

    async def check_conflicts(
        self,
        workspace_id: uuid.UUID,
        candidate_id: uuid.UUID,
        participant_user_ids: List[uuid.UUID],
        start_utc: datetime,
        end_utc: datetime,
        exclude_schedule_id: Optional[uuid.UUID],
        db: AsyncSession,
    ) -> None:
        """Strict interval-overlap conflict check: existing_start < requested_end AND existing_end > requested_start."""

        # 1. Candidate conflict check
        cand_conflict_stmt = (
            select(InterviewSchedule)
            .join(Interview, InterviewSchedule.interview_id == Interview.id)
            .where(
                Interview.candidate_id == candidate_id,
                InterviewSchedule.workspace_id == workspace_id,
                InterviewSchedule.status.in_([ScheduleStatus.CONFIRMED, ScheduleStatus.PENDING]),
                InterviewSchedule.scheduled_start_at < end_utc,
                InterviewSchedule.scheduled_end_at > start_utc,
                InterviewSchedule.is_deleted.is_(False),
            )
        )
        if exclude_schedule_id:
            cand_conflict_stmt = cand_conflict_stmt.where(InterviewSchedule.id != exclude_schedule_id)

        cand_conflict = (await db.execute(cand_conflict_stmt)).scalar_one_or_none()
        if cand_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Scheduling conflict: Candidate already has an interview scheduled from "
                       f"{cand_conflict.scheduled_start_at.strftime('%Y-%m-%d %H:%M UTC')} to "
                       f"{cand_conflict.scheduled_end_at.strftime('%H:%M UTC')}.",
            )

        # 2. Participants conflict check
        if participant_user_ids:
            part_conflict_stmt = (
                select(InterviewSchedule, User)
                .join(Interview, InterviewSchedule.interview_id == Interview.id)
                .join(InterviewParticipant, InterviewParticipant.interview_id == Interview.id)
                .join(User, InterviewParticipant.user_id == User.id)
                .where(
                    InterviewParticipant.user_id.in_(participant_user_ids),
                    InterviewSchedule.workspace_id == workspace_id,
                    InterviewSchedule.status.in_([ScheduleStatus.CONFIRMED, ScheduleStatus.PENDING]),
                    InterviewSchedule.scheduled_start_at < end_utc,
                    InterviewSchedule.scheduled_end_at > start_utc,
                    InterviewSchedule.is_deleted.is_(False),
                )
            )
            if exclude_schedule_id:
                part_conflict_stmt = part_conflict_stmt.where(InterviewSchedule.id != exclude_schedule_id)

            part_res = (await db.execute(part_conflict_stmt)).first()
            if part_res:
                conflict_sched, conflict_user = part_res
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Scheduling conflict: Interviewer {conflict_user.first_name} {conflict_user.last_name} "
                           f"already has a session from {conflict_sched.scheduled_start_at.strftime('%Y-%m-%d %H:%M UTC')} "
                           f"to {conflict_sched.scheduled_end_at.strftime('%H:%M UTC')}.",
                )

    async def schedule_interview(
        self,
        interview: Interview,
        scheduled_start_at: datetime,
        timezone_str: str,
        user_id: uuid.UUID,
        db: AsyncSession,
        allow_past: bool = False,
    ) -> InterviewSchedule:
        """Schedules an interview, validates readiness, locks duration, and checks conflicts."""

        # 1. Enforce readiness requirement from Phase 3
        is_ready, issues = await interview_service.validate_interview_readiness(interview, db)
        if not is_ready:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot schedule incomplete interview. Blocking issues: {'; '.join(issues)}",
            )

        # 2. Canonicalize time and calculate end time based on interview duration
        start_utc, end_utc = self.canonicalize_datetimes(
            start_dt=scheduled_start_at,
            tz_name=timezone_str,
            duration_minutes=interview.duration_minutes,
            allow_past=allow_past,
        )

        # 3. Check conflicts
        part_user_ids = [p.user_id for p in interview.participants]
        await self.check_conflicts(
            workspace_id=interview.workspace_id,
            candidate_id=interview.candidate_id,
            participant_user_ids=part_user_ids,
            start_utc=start_utc,
            end_utc=end_utc,
            exclude_schedule_id=None,
            db=db,
        )

        # 4. Check for existing active schedule and supersede
        existing_sched_stmt = select(InterviewSchedule).where(
            InterviewSchedule.interview_id == interview.id,
            InterviewSchedule.status.in_([ScheduleStatus.CONFIRMED, ScheduleStatus.PENDING]),
            InterviewSchedule.is_deleted.is_(False),
        )
        existing_sched = (await db.execute(existing_sched_stmt)).scalar_one_or_none()
        if existing_sched:
            existing_sched.status = ScheduleStatus.RESCHEDULED

        # 5. Create new schedule
        new_schedule = InterviewSchedule(
            interview_id=interview.id,
            workspace_id=interview.workspace_id,
            scheduled_start_at=start_utc,
            scheduled_end_at=end_utc,
            timezone=timezone_str,
            status=ScheduleStatus.CONFIRMED,
            created_by=user_id,
        )
        db.add(new_schedule)

        # 6. Update interview lifecycle state
        interview.status = InterviewStatus.SCHEDULED
        await db.flush()

        # 7. Create in-app notifications for participants
        for p in interview.participants:
            notif = Notification(
                workspace_id=interview.workspace_id,
                user_id=p.user_id,
                notification_type=NotificationType.INTERVIEW_SCHEDULED,
                title=f"Interview Scheduled: {interview.title}",
                message=f"Scheduled for {start_utc.strftime('%Y-%m-%d %H:%M UTC')} ({timezone_str}). Duration: {interview.duration_minutes}m.",
                extra_metadata={
                    "interview_id": str(interview.id),
                    "schedule_id": str(new_schedule.id),
                    "scheduled_start_at": start_utc.isoformat(),
                },
            )
            db.add(notif)

        await db.commit()
        await db.refresh(new_schedule)

        # 8. Trigger email notifications asynchronously
        start_str = start_utc.strftime("%B %d, %Y at %I:%M %p UTC")
        if interview.candidate:
            cand_name = f"{interview.candidate.first_name} {interview.candidate.last_name}"
            await email_service.send_interview_scheduled(
                to_email=interview.candidate.email,
                recipient_name=cand_name,
                interview_title=interview.title,
                start_time_str=start_str,
                timezone_str=timezone_str,
                duration_minutes=interview.duration_minutes,
            )

        return new_schedule

    async def reschedule_interview(
        self,
        schedule_id: uuid.UUID,
        new_start_at: datetime,
        new_timezone_str: str,
        user_id: uuid.UUID,
        db: AsyncSession,
        reason: Optional[str] = None,
        allow_past: bool = False,
    ) -> InterviewSchedule:
        """Reschedules an interview, archives previous times into history, and updates state."""

        sched_stmt = (
            select(InterviewSchedule)
            .where(InterviewSchedule.id == schedule_id, InterviewSchedule.is_deleted.is_(False))
            .options(
                selectinload(InterviewSchedule.interview).selectinload(Interview.candidate),
                selectinload(InterviewSchedule.interview).selectinload(Interview.participants),
            )
        )
        sched = (await db.execute(sched_stmt)).scalar_one_or_none()
        if not sched:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

        itw = sched.interview

        # 1. Canonicalize new times
        start_utc, end_utc = self.canonicalize_datetimes(
            start_dt=new_start_at,
            tz_name=new_timezone_str,
            duration_minutes=itw.duration_minutes,
            allow_past=allow_past,
        )

        # 2. Check conflicts
        part_user_ids = [p.user_id for p in itw.participants]
        await self.check_conflicts(
            workspace_id=sched.workspace_id,
            candidate_id=itw.candidate_id,
            participant_user_ids=part_user_ids,
            start_utc=start_utc,
            end_utc=end_utc,
            exclude_schedule_id=sched.id,
            db=db,
        )

        # 3. Create history record
        history_entry = InterviewScheduleHistory(
            schedule_id=sched.id,
            previous_start_at=sched.scheduled_start_at,
            previous_end_at=sched.scheduled_end_at,
            previous_timezone=sched.timezone,
            new_start_at=start_utc,
            new_end_at=end_utc,
            new_timezone=new_timezone_str,
            changed_by=user_id,
            reason=reason or "Rescheduled by organizer",
        )
        db.add(history_entry)

        # 4. Update schedule
        sched.scheduled_start_at = start_utc
        sched.scheduled_end_at = end_utc
        sched.timezone = new_timezone_str
        sched.status = ScheduleStatus.CONFIRMED

        # 5. Create in-app notifications
        for p in itw.participants:
            notif = Notification(
                workspace_id=sched.workspace_id,
                user_id=p.user_id,
                notification_type=NotificationType.INTERVIEW_RESCHEDULED,
                title=f"Interview Rescheduled: {itw.title}",
                message=f"New time: {start_utc.strftime('%Y-%m-%d %H:%M UTC')} ({new_timezone_str}). Reason: {reason or 'None'}",
                extra_metadata={"interview_id": str(itw.id), "schedule_id": str(sched.id)},
            )
            db.add(notif)

        await db.commit()
        await db.refresh(sched)

        # 6. Email notifications
        if itw.candidate:
            cand_name = f"{itw.candidate.first_name} {itw.candidate.last_name}"
            await email_service.send_interview_rescheduled(
                to_email=itw.candidate.email,
                recipient_name=cand_name,
                interview_title=itw.title,
                new_start_time_str=start_utc.strftime("%B %d, %Y at %I:%M %p UTC"),
                new_timezone_str=new_timezone_str,
                reason=reason,
            )

        return sched

    async def cancel_schedule(
        self,
        schedule_id: uuid.UUID,
        user_id: uuid.UUID,
        cancellation_reason: Optional[str],
        db: AsyncSession,
    ) -> InterviewSchedule:
        """Cancels an active interview schedule without deleting history."""

        sched_stmt = (
            select(InterviewSchedule)
            .where(InterviewSchedule.id == schedule_id, InterviewSchedule.is_deleted.is_(False))
            .options(
                selectinload(InterviewSchedule.interview).selectinload(Interview.candidate),
                selectinload(InterviewSchedule.interview).selectinload(Interview.participants),
            )
        )
        sched = (await db.execute(sched_stmt)).scalar_one_or_none()
        if not sched:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

        sched.status = ScheduleStatus.CANCELLED
        sched.cancelled_at = datetime.now(timezone.utc)
        sched.cancelled_by = user_id
        sched.cancellation_reason = cancellation_reason or "Cancelled by organizer"

        # Revert interview state to READY so it can be scheduled again
        itw = sched.interview
        itw.status = InterviewStatus.READY

        # Notifications
        for p in itw.participants:
            notif = Notification(
                workspace_id=sched.workspace_id,
                user_id=p.user_id,
                notification_type=NotificationType.INTERVIEW_CANCELLED,
                title=f"Interview Cancelled: {itw.title}",
                message=f"Session cancelled. Reason: {cancellation_reason or 'None'}",
                extra_metadata={"interview_id": str(itw.id)},
            )
            db.add(notif)

        await db.commit()
        await db.refresh(sched)

        # Send cancellation email
        if itw.candidate:
            cand_name = f"{itw.candidate.first_name} {itw.candidate.last_name}"
            await email_service.send_interview_cancelled(
                to_email=itw.candidate.email,
                recipient_name=cand_name,
                interview_title=itw.title,
                reason=cancellation_reason,
            )

        return sched

    async def generate_available_slots(
        self,
        interview: Interview,
        target_date: date,
        timezone_str: str,
        db: AsyncSession,
    ) -> AvailableSlotsResponse:
        """Calculates discrete available interview slots matching interview.duration_minutes."""

        zi = self.validate_timezone(timezone_str)
        duration_mins = interview.duration_minutes

        # Working hours standard window: 09:00 to 18:00 in target timezone
        day_start_local = datetime.combine(target_date, time(9, 0)).replace(tzinfo=zi)
        day_end_local = datetime.combine(target_date, time(18, 0)).replace(tzinfo=zi)

        day_start_utc = day_start_local.astimezone(timezone.utc)
        day_end_utc = day_end_local.astimezone(timezone.utc)

        # Retrieve existing confirmed schedules for workspace within day
        part_user_ids = [p.user_id for p in interview.participants]
        conflicts_stmt = (
            select(InterviewSchedule)
            .join(Interview, InterviewSchedule.interview_id == Interview.id)
            .where(
                InterviewSchedule.workspace_id == interview.workspace_id,
                InterviewSchedule.status.in_([ScheduleStatus.CONFIRMED, ScheduleStatus.PENDING]),
                InterviewSchedule.scheduled_start_at < day_end_utc,
                InterviewSchedule.scheduled_end_at > day_start_utc,
                InterviewSchedule.is_deleted.is_(False),
                or_(
                    Interview.candidate_id == interview.candidate_id,
                    InterviewSchedule.interview_id.in_(
                        select(InterviewParticipant.interview_id).where(
                            InterviewParticipant.user_id.in_(part_user_ids)
                        )
                    ) if part_user_ids else False,
                ),
            )
        )
        existing_schedules = (await db.execute(conflicts_stmt)).scalars().all()

        # Generate 30-minute increment slots
        candidate_slots: List[AvailableSlot] = []
        cursor_utc = day_start_utc
        step_minutes = 30

        while cursor_utc + timedelta(minutes=duration_mins) <= day_end_utc:
            slot_end_utc = cursor_utc + timedelta(minutes=duration_mins)

            # Check if this slot overlaps any existing schedule
            has_conflict = any(
                sched.scheduled_start_at < slot_end_utc and sched.scheduled_end_at > cursor_utc
                for sched in existing_schedules
            )

            # Check if slot is in the past
            is_past = cursor_utc < datetime.now(timezone.utc)

            if not has_conflict and not is_past:
                candidate_slots.append(
                    AvailableSlot(
                        start_at=cursor_utc,
                        end_at=slot_end_utc,
                        duration_minutes=duration_mins,
                    )
                )

            cursor_utc += timedelta(minutes=step_minutes)

        return AvailableSlotsResponse(
            requested_date=target_date.isoformat(),
            timezone=timezone_str,
            duration_minutes=duration_mins,
            slots=candidate_slots,
        )


scheduling_service = SchedulingService()

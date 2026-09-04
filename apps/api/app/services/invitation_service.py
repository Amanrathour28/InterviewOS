import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.scheduling import InterviewInvitation, InvitationStatus, RecipientType
from app.models.user import User
from app.schemas.scheduling import PublicInvitationDetail
from app.services.email_service import email_service


class InvitationService:
    """Manages secure invitation tokens, SHA-256 hashing at rest, and accept/decline flows."""

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_invitation(
        self,
        interview_id: uuid.UUID,
        workspace_id: uuid.UUID,
        email: str,
        recipient_type: RecipientType,
        recipient_user_id: Optional[uuid.UUID],
        recipient_candidate_id: Optional[uuid.UUID],
        db: AsyncSession,
        base_url: str = "http://localhost:3000",
    ) -> Tuple[InterviewInvitation, str]:
        """Generates a cryptographically secure invitation, stores its hash, and triggers email."""
        # 1. Generate raw 32-byte url-safe token
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)

        # 2. Expiration (7 days from now in UTC)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = InterviewInvitation(
            interview_id=interview_id,
            workspace_id=workspace_id,
            recipient_user_id=recipient_user_id,
            recipient_candidate_id=recipient_candidate_id,
            recipient_type=recipient_type,
            email=email.lower().strip(),
            token_hash=token_hash,
            status=InvitationStatus.SENT,
            expires_at=expires_at,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)

        # 3. Resolve interview details for email notification
        itw_stmt = (
            select(Interview)
            .where(Interview.id == interview_id)
            .options(selectinload(Interview.schedules))
        )
        itw = (await db.execute(itw_stmt)).scalar_one_or_none()

        start_time_str = "TBD"
        tz_str = "UTC"
        duration_mins = itw.duration_minutes if itw else 60

        if itw and itw.schedules:
            active_sched = next((s for s in itw.schedules if s.status.value in ["confirmed", "pending"]), None)
            if active_sched:
                start_time_str = active_sched.scheduled_start_at.strftime("%B %d, %Y at %I:%M %p UTC")
                tz_str = active_sched.timezone

        recipient_name = email.split("@")[0].capitalize()
        invite_url = f"{base_url}/invite/{raw_token}"

        await email_service.send_interview_invitation(
            to_email=email,
            recipient_name=recipient_name,
            interview_title=itw.title if itw else "Technical Interview",
            start_time_str=start_time_str,
            timezone_str=tz_str,
            duration_minutes=duration_mins,
            invite_url=invite_url,
        )

        return invitation, raw_token

    async def get_invitation_by_token(self, token: str, db: AsyncSession) -> InterviewInvitation:
        token_hash = self._hash_token(token)
        stmt = (
            select(InterviewInvitation)
            .where(InterviewInvitation.token_hash == token_hash)
            .options(
                selectinload(InterviewInvitation.interview).selectinload(Interview.schedules),
                selectinload(InterviewInvitation.interview).selectinload(Interview.candidate),
                selectinload(InterviewInvitation.interview).selectinload(Interview.job),
                selectinload(InterviewInvitation.interview).selectinload(Interview.participants).selectinload(
                    Interview.participants.property.mapper.class_.user
                ),
            )
        )
        res = await db.execute(stmt)
        invitation = res.scalar_one_or_none()
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation link is invalid or has been revoked.",
            )

        # Check expiration
        now_utc = datetime.now(timezone.utc)
        exp_utc = invitation.expires_at if invitation.expires_at.tzinfo else invitation.expires_at.replace(tzinfo=timezone.utc)
        if exp_utc < now_utc:
            invitation.status = InvitationStatus.EXPIRED
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This invitation link has expired.",
            )

        return invitation

    async def get_public_invitation_detail(self, token: str, db: AsyncSession) -> PublicInvitationDetail:
        """Returns non-sensitive public interview metadata for invitation acceptance screen."""
        invitation = await self.get_invitation_by_token(token, db)
        itw = invitation.interview

        # Find confirmed schedule
        active_sched = next((s for s in itw.schedules if s.status.value in ["confirmed", "pending"]), None)
        if not active_sched:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This interview has not been scheduled yet.",
            )

        interviewer_names = [
            f"{p.user.first_name} {p.user.last_name}"
            for p in itw.participants
            if p.user
        ]

        return PublicInvitationDetail(
            interview_id=itw.id,
            title=itw.title,
            description=itw.description,
            scheduled_start_at=active_sched.scheduled_start_at,
            scheduled_end_at=active_sched.scheduled_end_at,
            timezone=active_sched.timezone,
            duration_minutes=itw.duration_minutes,
            candidate_name=f"{itw.candidate.first_name} {itw.candidate.last_name}" if itw.candidate else None,
            job_title=itw.job.title if itw.job else None,
            interviewer_names=interviewer_names,
            status=invitation.status,
            expires_at=invitation.expires_at,
        )

    async def accept_invitation(self, token: str, db: AsyncSession) -> InterviewInvitation:
        invitation = await self.get_invitation_by_token(token, db)
        if invitation.status == InvitationStatus.ACCEPTED:
            return invitation
        if invitation.status == InvitationStatus.DECLINED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation was previously declined.",
            )

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(invitation)
        return invitation

    async def decline_invitation(self, token: str, db: AsyncSession, reason: Optional[str] = None) -> InterviewInvitation:
        invitation = await self.get_invitation_by_token(token, db)
        if invitation.status == InvitationStatus.DECLINED:
            return invitation

        invitation.status = InvitationStatus.DECLINED
        invitation.declined_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(invitation)
        return invitation


invitation_service = InvitationService()

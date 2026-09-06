import enum
import uuid
from datetime import datetime, time
from typing import Optional
import sqlalchemy as sa
from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ScheduleStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    COMPLETED = "completed"


class RecipientType(str, enum.Enum):
    CANDIDATE = "candidate"
    LEAD_INTERVIEWER = "lead_interviewer"
    INTERVIEWER = "interviewer"
    OBSERVER = "observer"
    RECRUITER = "recruiter"


class InvitationStatus(str, enum.Enum):
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class NotificationType(str, enum.Enum):
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_RESCHEDULED = "interview_rescheduled"
    INTERVIEW_CANCELLED = "interview_cancelled"
    INTERVIEW_REMINDER = "interview_reminder"
    INVITATION_RECEIVED = "invitation_received"


class InterviewSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "interview_schedules"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    scheduled_end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)  # IANA identifier, e.g. "Asia/Kolkata"
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus, native_enum=False, length=32),
        default=ScheduleStatus.CONFIRMED,
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    interview = relationship("Interview", back_populates="schedules")
    workspace = relationship("Workspace")
    creator = relationship("User", foreign_keys=[created_by])
    canceller = relationship("User", foreign_keys=[cancelled_by])
    history = relationship(
        "InterviewScheduleHistory",
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="InterviewScheduleHistory.created_at.desc()",
    )


class InterviewScheduleHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "interview_schedule_history"

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    new_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    schedule = relationship("InterviewSchedule", back_populates="history")
    changer = relationship("User")


class UserAvailability(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_availability"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)     # e.g. 09:00:00
    end_time: Mapped[time] = mapped_column(Time, nullable=False)       # e.g. 17:00:00
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)  # IANA timezone
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User")
    workspace = relationship("Workspace")


class AvailabilityException(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "availability_exceptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    exception_type: Mapped[str] = mapped_column(String(32), default="leave", nullable=False)  # leave, holiday, blocked
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    user = relationship("User")
    workspace = relationship("Workspace")


class InterviewInvitation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_invitations"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    recipient_candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    recipient_type: Mapped[RecipientType] = mapped_column(
        Enum(RecipientType, native_enum=False, length=32),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, native_enum=False, length=32),
        default=InvitationStatus.SENT,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    declined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Candidate identity fields — populated when the guest enters their details.
    # Raw candidate session token is NEVER stored; only its SHA-256 hash is persisted.
    candidate_session_token_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    candidate_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    candidate_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    interview = relationship("Interview", back_populates="invitations")
    workspace = relationship("Workspace")
    recipient_user = relationship("User")
    recipient_candidate = relationship("Candidate")


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=32),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    workspace = relationship("Workspace")
    user = relationship("User")

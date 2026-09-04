import enum
import sqlalchemy as sa
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SessionStatus(str, enum.Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SessionStage(str, enum.Enum):
    INTRODUCTION = "introduction"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    CODING = "coding"
    SYSTEM_DESIGN = "system_design"
    CLOSING = "closing"
    COMPLETED = "completed"


class InterviewSession(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Represents a live, execution instance of a scheduled interview."""

    __tablename__ = "interview_sessions"
    __table_args__ = (
        Index("ix_interview_sessions_interview_id", "interview_id"),
        Index("ix_interview_sessions_workspace_id", "workspace_id"),
        Index("ix_interview_sessions_status", "status"),
        Index("ix_interview_sessions_started_at", "started_at"),
    )

    interview_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    status = Column(
        Enum(SessionStatus, native_enum=False),
        nullable=False,
        default=SessionStatus.WAITING,
    )
    current_stage = Column(String(64), nullable=False, default=SessionStage.INTRODUCTION.value)
    stage_started_at = Column(DateTime(timezone=True), nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    total_paused_seconds = Column(Integer, nullable=False, default=0)

    last_event_sequence = Column(Integer, nullable=False, default=0)
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    interview = relationship("Interview", back_populates="sessions")
    workspace = relationship("Workspace")
    creator = relationship("User")
    events = relationship(
        "InterviewEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewEvent.sequence",
        lazy="selectin",
    )


class InterviewEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Authoritative durable event log for an interview session."""

    __tablename__ = "interview_events"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_interview_event_sequence"),
        Index("ix_interview_events_session_id", "session_id"),
        Index("ix_interview_events_event_type", "event_type"),
        Index("ix_interview_events_created_at", "created_at"),
    )

    session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(64), nullable=False)
    actor_id = Column(sa.Uuid(as_uuid=True), nullable=True)
    actor_role = Column(String(32), nullable=False, default="system")
    sequence = Column(Integer, nullable=False)

    # JSON payload storage
    payload = Column(
        JSONB().with_variant(sa.JSON, "sqlite"),
        nullable=False,
        default=dict,
    )

    # Relationships
    session = relationship("InterviewSession", back_populates="events")


class NoteCategory(str, enum.Enum):
    GENERAL = "general"
    RUBRIC = "rubric"
    CODING = "coding"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"


class InterviewerNote(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Structured private evaluation note taken by an interviewer during a session."""

    __tablename__ = "interviewer_notes"
    __table_args__ = (
        Index("ix_interviewer_notes_session_id", "session_id"),
        Index("ix_interviewer_notes_user_id", "user_id"),
        Index("ix_interviewer_notes_category", "category"),
    )

    session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category = Column(
        Enum(NoteCategory, native_enum=False),
        nullable=False,
        default=NoteCategory.GENERAL,
    )
    stage = Column(String(64), nullable=True)
    content = Column(Text, nullable=False, default="")
    rating = Column(Integer, nullable=True)
    tags = Column(
        JSONB().with_variant(sa.JSON, "sqlite"),
        nullable=False,
        default=list,
    )

    # Relationships
    session = relationship("InterviewSession", backref="notes")
    user = relationship("User")


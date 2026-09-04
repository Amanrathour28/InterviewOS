import uuid
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Whiteboard(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a collaborative whiteboard workspace attached to an InterviewSession."""

    __tablename__ = "whiteboards"
    __table_args__ = (
        Index("ix_whiteboards_interview_session_id", "interview_session_id", unique=True),
        Index("ix_whiteboards_workspace_id", "workspace_id"),
    )

    interview_session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False, default="System Design Whiteboard")
    is_locked = Column(Boolean, nullable=False, default=False)
    document_json = Column(
        "document",
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    private_layer_json = Column(
        "private_layer",
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    interview_session = relationship("InterviewSession", backref="whiteboard")
    workspace = relationship("Workspace")
    creator = relationship("User")
    snapshots = relationship(
        "WhiteboardSnapshot",
        back_populates="whiteboard",
        cascade="all, delete-orphan",
        order_by="WhiteboardSnapshot.snapshot_number.desc()",
        lazy="selectin",
    )


class WhiteboardSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an immutable architectural milestone checkpoint of the whiteboard."""

    __tablename__ = "whiteboard_snapshots"
    __table_args__ = (
        Index("ix_whiteboard_snapshots_whiteboard_id", "whiteboard_id"),
        Index("ix_whiteboard_snapshots_created_at", "created_at"),
    )

    whiteboard_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("whiteboards.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_number = Column(Integer, nullable=False, default=1)
    label = Column(String(255), nullable=False, default="Milestone Checkpoint")
    source = Column(String(32), nullable=False, default="manual")
    document_json = Column(
        "document",
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    private_layer_json = Column(
        "private_layer",
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    # Relationships
    whiteboard = relationship("Whiteboard", back_populates="snapshots")
    creator = relationship("User")

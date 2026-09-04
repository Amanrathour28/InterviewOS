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


class ChatChannelType(str, enum.Enum):
    PUBLIC = "public"
    INTERVIEWER_PRIVATE = "interviewer_private"


class ChatMessageType(str, enum.Enum):
    TEXT = "text"
    CODE = "code"
    SYSTEM = "system"


class ChatChannel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an isolated communication channel within an interview session."""

    __tablename__ = "chat_channels"
    __table_args__ = (
        Index("ix_chat_channels_session_id", "session_id"),
        Index("ix_chat_channels_workspace_id", "workspace_id"),
        Index("ix_chat_channels_type", "channel_type"),
        UniqueConstraint("session_id", "channel_type", name="uq_session_channel_type"),
    )

    session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_type = Column(
        Enum(ChatChannelType, native_enum=False),
        nullable=False,
        default=ChatChannelType.PUBLIC,
    )
    name = Column(String(128), nullable=False)

    # Relationships
    messages = relationship(
        "ChatMessage",
        back_populates="channel",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    read_states = relationship(
        "ChatReadState",
        back_populates="channel",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Represents a persistent chat message or structured code snippet."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_channel_id", "channel_id"),
        Index("ix_chat_messages_session_id", "session_id"),
        Index("ix_chat_messages_workspace_id", "workspace_id"),
        Index("ix_chat_messages_parent_message_id", "parent_message_id"),
        Index("ix_chat_messages_created_at", "created_at"),
        Index("ix_chat_messages_channel_created", "channel_id", "created_at"),
        Index("ix_chat_messages_client_id", "channel_id", "client_message_id"),
    )

    channel_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("chat_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_name = Column(String(255), nullable=False)
    sender_role = Column(String(64), nullable=False)
    parent_message_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=True,
    )
    message_type = Column(
        Enum(ChatMessageType, native_enum=False),
        nullable=False,
        default=ChatMessageType.TEXT,
    )
    content = Column(Text, nullable=False)
    metadata_json = Column(
        "metadata",
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    client_message_id = Column(String(64), nullable=True)
    is_edited = Column(Boolean, nullable=False, default=False)

    # Relationships
    channel = relationship("ChatChannel", back_populates="messages")
    parent_message = relationship(
        "ChatMessage",
        remote_side="ChatMessage.id",
        back_populates="replies",
    )
    replies = relationship(
        "ChatMessage",
        back_populates="parent_message",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
        lazy="selectin",
    )
    reactions = relationship(
        "ChatReaction",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ChatReaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an emoji reaction attached to a message."""

    __tablename__ = "chat_reactions"
    __table_args__ = (
        Index("ix_chat_reactions_message_id", "message_id"),
        Index("ix_chat_reactions_user_id", "user_id"),
        UniqueConstraint("message_id", "user_id", "emoji", name="uq_chat_reaction_user_emoji"),
    )

    message_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_name = Column(String(255), nullable=False)
    emoji = Column(String(16), nullable=False)

    # Relationships
    message = relationship("ChatMessage", back_populates="reactions")


class ChatReadState(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks the last-read message cursor for a user in a channel."""

    __tablename__ = "chat_read_states"
    __table_args__ = (
        Index("ix_chat_read_states_channel_user", "channel_id", "user_id"),
        UniqueConstraint("channel_id", "user_id", name="uq_chat_read_state_user"),
    )

    channel_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("chat_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    last_read_message_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_read_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    channel = relationship("ChatChannel", back_populates="read_states")

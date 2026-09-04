import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Boolean, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Server-side tracked session storing hashed refresh tokens for revocable auth."""
    __tablename__ = "refresh_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_sessions")


class PasswordResetToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks one-time password reset tokens."""
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User")

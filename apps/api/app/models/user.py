import enum
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.organization import OrganizationMembership
    from app.models.workspace import WorkspaceMembership
    from app.models.auth import RefreshSession


class UserRole(str, enum.Enum):
    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"
    RECRUITER = "recruiter"
    ORGANIZATION_ADMIN = "organization_admin"
    PLATFORM_ADMIN = "platform_admin"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """User account model supporting multi-role RBAC."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    
    # Global role (default: candidate)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=False),
        default=UserRole.CANDIDATE,
        nullable=False,
        index=True,
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    organization_memberships: Mapped[List["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    workspace_memberships: Mapped[List["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_sessions: Mapped[List["RefreshSession"]] = relationship(
        "RefreshSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

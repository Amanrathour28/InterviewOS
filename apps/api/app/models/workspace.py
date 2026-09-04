import enum
import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, Enum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class WorkspaceMemberRole(str, enum.Enum):
    ADMIN = "admin"
    INTERVIEWER = "interviewer"
    RECRUITER = "recruiter"
    MEMBER = "member"


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Workspace belonging to an Organization."""
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="workspaces")
    memberships: Mapped[List["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    jobs = relationship("Job", back_populates="workspace", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="workspace", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="workspace", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="workspace", cascade="all, delete-orphan")
    interview_templates = relationship("InterviewTemplate", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates a User with a Workspace with specific workspace permissions."""
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[WorkspaceMemberRole] = mapped_column(
        Enum(WorkspaceMemberRole, name="workspace_member_role_enum", native_enum=False),
        default=WorkspaceMemberRole.MEMBER,
        nullable=False,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="workspace_memberships")

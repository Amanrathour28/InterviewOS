import enum
import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, UniqueConstraint, Enum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class OrgMemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Organization tenant entity."""
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    workspaces: Mapped[List["Workspace"]] = relationship(
        "Workspace",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class OrganizationMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates a User with an Organization with specific role permissions."""
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrgMemberRole] = mapped_column(
        Enum(OrgMemberRole, name="org_member_role_enum", native_enum=False),
        default=OrgMemberRole.MEMBER,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="organization_memberships")

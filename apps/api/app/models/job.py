import enum
from typing import List, Optional
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class JobPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A job requisition belonging to a specific workspace."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_workspace_status", "workspace_id", "status"),
        Index("ix_jobs_workspace_slug", "workspace_id", "slug"),
    )

    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    department = Column(String(100), nullable=True)
    location = Column(String(150), nullable=True)
    employment_type = Column(
        Enum(EmploymentType, native_enum=False),
        nullable=False,
        default=EmploymentType.FULL_TIME,
    )

    experience_min = Column(Integer, nullable=True)
    experience_max = Column(Integer, nullable=True)

    status = Column(
        Enum(JobStatus, native_enum=False),
        nullable=False,
        default=JobStatus.OPEN,
        index=True,
    )
    priority = Column(
        Enum(JobPriority, native_enum=False),
        nullable=False,
        default=JobPriority.MEDIUM,
    )

    # Skills and requirements stored as JSON lists for portability and fast retrieval
    required_skills = Column(JSON, nullable=False, default=list)
    preferred_skills = Column(JSON, nullable=False, default=list)
    responsibilities = Column(JSON, nullable=False, default=list)
    requirements = Column(JSON, nullable=False, default=list)

    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=False, default="USD")

    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="jobs")
    creator = relationship("User")
    candidate_applications = relationship(
        "JobCandidate",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

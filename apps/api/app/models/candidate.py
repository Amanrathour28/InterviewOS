import enum
from datetime import datetime, timezone
from typing import List, Optional
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
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


class CandidateStatus(str, enum.Enum):
    NEW = "new"
    SCREENING = "screening"
    SHORTLISTED = "shortlisted"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CandidateSource(str, enum.Enum):
    REFERRAL = "referral"
    LINKEDIN = "linkedin"
    INBOUND = "inbound"
    AGENCY = "agency"
    CAREER_PAGE = "career_page"
    OTHER = "other"


class DocumentType(str, enum.Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    OTHER = "other"


class Candidate(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Candidate entity scoped to a technical workspace."""

    __tablename__ = "candidates"
    __table_args__ = (
        Index("ix_candidates_workspace_status", "workspace_id", "status"),
        Index("ix_candidates_workspace_email", "workspace_id", "email"),
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

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(150), nullable=True)
    headline = Column(String(255), nullable=True)

    current_company = Column(String(150), nullable=True)
    current_title = Column(String(150), nullable=True)
    experience_years = Column(Float, nullable=True)
    education_summary = Column(Text, nullable=True)

    linkedin_url = Column(String(255), nullable=True)
    github_url = Column(String(255), nullable=True)
    portfolio_url = Column(String(255), nullable=True)

    status = Column(
        Enum(CandidateStatus, native_enum=False),
        nullable=False,
        default=CandidateStatus.NEW,
        index=True,
    )
    source = Column(
        Enum(CandidateSource, native_enum=False),
        nullable=False,
        default=CandidateSource.INBOUND,
    )
    notes_summary = Column(Text, nullable=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="candidates")
    creator = relationship("User")
    job_applications = relationship(
        "JobCandidate",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents = relationship(
        "CandidateDocument",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notes = relationship(
        "CandidateNote",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    activities = relationship(
        "CandidateActivity",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tag_assignments = relationship(
        "CandidateTagAssignment",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class JobCandidate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """M2M relationship tracking candidate applications across jobs."""

    __tablename__ = "job_candidates"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),
        Index("ix_job_candidates_job_status", "job_id", "status"),
    )

    job_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(CandidateStatus, native_enum=False),
        nullable=False,
        default=CandidateStatus.NEW,
    )
    source = Column(String(50), nullable=True)
    applied_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_activity_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    job = relationship("Job", back_populates="candidate_applications")
    candidate = relationship("Candidate", back_populates="job_applications")


class CandidateTag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Workspace-scoped candidate tags."""

    __tablename__ = "candidate_tags"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_tag_name"),
    )

    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(50), nullable=False)
    color = Column(String(20), nullable=False, default="#6366f1")

    # Relationships
    tag_assignments = relationship(
        "CandidateTagAssignment",
        back_populates="tag",
        cascade="all, delete-orphan",
    )


class CandidateTagAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """M2M link between candidates and tags."""

    __tablename__ = "candidate_tag_assignments"
    __table_args__ = (
        UniqueConstraint("tag_id", "candidate_id", name="uq_tag_candidate"),
    )

    tag_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidate_tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tag = relationship("CandidateTag", back_populates="tag_assignments")
    candidate = relationship("Candidate", back_populates="tag_assignments")


class CandidateNote(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Internal recruiter/interviewer notes on candidates."""

    __tablename__ = "candidate_notes"

    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    content = Column(Text, nullable=False)

    # Relationships
    candidate = relationship("Candidate", back_populates="notes")
    author = relationship("User")


class CandidateDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Metadata tracking candidate resumes and attachments in object storage."""

    __tablename__ = "candidate_documents"

    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    file_name = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False, unique=True)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    document_type = Column(
        Enum(DocumentType, native_enum=False),
        nullable=False,
        default=DocumentType.RESUME,
    )

    # Relationships
    candidate = relationship("Candidate", back_populates="documents")
    uploader = relationship("User")


class CandidateActivity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit log / timeline tracking candidate updates and events."""

    __tablename__ = "candidate_activities"

    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type = Column(String(50), nullable=False, index=True)
    details = Column(JSON, nullable=False, default=dict)

    # Relationships
    candidate = relationship("Candidate", back_populates="activities")
    actor = relationship("User")

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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


class ParsingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ClaimStatus(str, enum.Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"


class RequirementType(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    INFERRED = "inferred"


class BlueprintStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    APPLIED = "applied"
    ARCHIVED = "archived"


class QuestionPlanStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    APPLIED = "applied"
    ARCHIVED = "archived"


class ResumeVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Tracks historical and active resume uploads with parsing status and extracted text."""

    __tablename__ = "resume_versions"
    __table_args__ = (
        Index("ix_resume_versions_candidate_active", "candidate_id", "is_active"),
    )

    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    version_number = Column(Integer, nullable=False, default=1)
    file_name = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    parsing_status = Column(
        Enum(ParsingStatus, native_enum=False),
        nullable=False,
        default=ParsingStatus.PENDING,
    )
    parser_version = Column(String(50), nullable=False, default="1.0")
    extracted_text = Column(Text, nullable=True)
    extraction_metadata = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=True)

    # Relationships
    candidate = relationship("Candidate", lazy="selectin")
    profile = relationship(
        "ResumeProfile",
        back_populates="resume_version",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    claims = relationship(
        "ResumeClaim",
        back_populates="resume_version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ResumeProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured extraction of candidate skills, experience, education, and projects."""

    __tablename__ = "resume_profiles"
    __table_args__ = (
        UniqueConstraint("resume_version_id", name="uq_resume_profile_version"),
    )

    resume_version_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    summary = Column(Text, nullable=False, default="")
    experience_years = Column(Float, nullable=True)
    seniority_level = Column(String(50), nullable=True)

    skills = Column(JSON, nullable=False, default=list)
    experience = Column(JSON, nullable=False, default=list)
    education = Column(JSON, nullable=False, default=list)
    projects = Column(JSON, nullable=False, default=list)
    certifications = Column(JSON, nullable=False, default=list)
    achievements = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.8)

    resume_version = relationship("ResumeVersion", back_populates="profile")


class ResumeClaim(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific technical/architectural claim extracted from resume with provenance."""

    __tablename__ = "resume_claims"
    __table_args__ = (
        Index("ix_resume_claims_category", "category"),
    )

    resume_version_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    claim = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, default="general")
    status = Column(
        Enum(ClaimStatus, native_enum=False),
        nullable=False,
        default=ClaimStatus.EXPLICIT,
    )
    confidence = Column(Float, nullable=False, default=0.9)
    verification_priority = Column(String(20), nullable=False, default="medium")  # high, medium, low
    evidence = Column(JSON, nullable=False, default=dict)  # {source, page, text}
    suggested_probes = Column(JSON, nullable=False, default=list)  # list of probe question strings

    resume_version = relationship("ResumeVersion", back_populates="claims")


class JobProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured intelligence profile extracted from Job Description."""

    __tablename__ = "job_profiles"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_job_profile_job"),
    )

    job_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    seniority = Column(String(50), nullable=False, default="mid")
    technical_domains = Column(JSON, nullable=False, default=list)
    responsibilities = Column(JSON, nullable=False, default=list)
    interview_focus = Column(JSON, nullable=False, default=list)
    suggested_rounds = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.85)

    requirements = relationship(
        "JobRequirement",
        back_populates="job_profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class JobRequirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual skill or competency requirement with importance and classification."""

    __tablename__ = "job_requirements"

    job_profile_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("job_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    skill = Column(String(150), nullable=False)
    canonical_skill = Column(String(150), nullable=False, index=True)
    category = Column(String(100), nullable=False, default="general")
    requirement_type = Column(
        Enum(RequirementType, native_enum=False),
        nullable=False,
        default=RequirementType.REQUIRED,
    )
    importance = Column(Float, nullable=False, default=1.0)  # 0.0 - 3.0 scale
    confidence = Column(Float, nullable=False, default=0.9)
    evidence = Column(Text, nullable=True)

    job_profile = relationship("JobProfile", back_populates="requirements")


class CandidateJobMatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Deterministic match evaluation between candidate and job with explainable breakdown."""

    __tablename__ = "candidate_job_matches"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_candidate_job_match"),
        Index("ix_matches_workspace_overall", "workspace_id", "overall_score"),
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
    resume_version_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    overall_score = Column(Float, nullable=False, default=0.0)  # 0 - 100
    required_skill_coverage = Column(Float, nullable=False, default=0.0)  # 0 - 100
    preferred_skill_coverage = Column(Float, nullable=False, default=0.0)  # 0 - 100
    experience_fit = Column(Float, nullable=False, default=0.0)  # 0 - 100
    project_relevance = Column(Float, nullable=False, default=0.0)  # 0 - 100
    seniority_fit = Column(Float, nullable=False, default=0.0)  # 0 - 100
    domain_fit = Column(Float, nullable=False, default=0.0)  # 0 - 100

    scoring_weights = Column(JSON, nullable=False, default=dict)
    strengths = Column(JSON, nullable=False, default=list)  # list of {skill, evidence}
    gaps = Column(JSON, nullable=False, default=list)  # list of {skill, reason}
    verification_areas = Column(JSON, nullable=False, default=list)  # list of {topic, questions}
    explanation = Column(Text, nullable=True)


class InterviewBlueprint(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Interview structure recommendation layer requiring explicit interviewer approval."""

    __tablename__ = "interview_blueprints"
    __table_args__ = (
        Index("ix_blueprints_workspace_status", "workspace_id", "status"),
    )

    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    interview_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    generated_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    version_number = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    status = Column(
        Enum(BlueprintStatus, native_enum=False),
        nullable=False,
        default=BlueprintStatus.DRAFT,
    )
    total_duration_minutes = Column(Integer, nullable=False, default=60)
    target_seniority = Column(String(50), nullable=False, default="mid")
    candidate_focus_areas = Column(JSON, nullable=False, default=list)
    job_focus_areas = Column(JSON, nullable=False, default=list)
    verification_priorities = Column(JSON, nullable=False, default=list)
    scoring_rubric = Column(JSON, nullable=False, default=dict)
    prompt_version = Column(String(50), nullable=False, default="interview_blueprint:v1")
    approved_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    rounds = relationship(
        "InterviewBlueprintRound",
        back_populates="blueprint",
        cascade="all, delete-orphan",
        order_by="InterviewBlueprintRound.sequence",
        lazy="selectin",
    )


class InterviewBlueprintRound(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An individual round recommendation within an interview blueprint."""

    __tablename__ = "interview_blueprint_rounds"
    __table_args__ = (
        UniqueConstraint("blueprint_id", "sequence", name="uq_blueprint_round_seq"),
    )

    blueprint_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(150), nullable=False)
    round_type = Column(String(50), nullable=False, default="technical")
    sequence = Column(Integer, nullable=False, default=1)
    duration_minutes = Column(Integer, nullable=False, default=30)
    difficulty = Column(String(50), nullable=False, default="mid")
    objectives = Column(JSON, nullable=False, default=list)
    competencies = Column(JSON, nullable=False, default=list)
    topics = Column(JSON, nullable=False, default=list)
    suggested_question_count = Column(Integer, nullable=False, default=3)
    scoring_weight = Column(Float, nullable=False, default=1.0)

    blueprint = relationship("InterviewBlueprint", back_populates="rounds")


class QuestionPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Personalized, evidence-grounded question sequence and coverage matrix."""

    __tablename__ = "question_plans"

    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interview_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    blueprint_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_blueprints.id", ondelete="SET NULL"),
        nullable=True,
    )
    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    version_number = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    status = Column(
        Enum(QuestionPlanStatus, native_enum=False),
        nullable=False,
        default=QuestionPlanStatus.DRAFT,
    )
    coverage_summary = Column(JSON, nullable=False, default=dict)  # {covered_count, total_requirements, matrix: [...]}
    prompt_version = Column(String(50), nullable=False, default="question_plan:v1")
    approved_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    items = relationship(
        "QuestionPlanItem",
        back_populates="question_plan",
        cascade="all, delete-orphan",
        order_by="QuestionPlanItem.sequence",
        lazy="selectin",
    )


class QuestionPlanItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An individual question item in the question plan with rationale and evidence link."""

    __tablename__ = "question_plan_items"
    __table_args__ = (
        UniqueConstraint("question_plan_id", "sequence", name="uq_plan_item_seq"),
    )

    question_plan_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("question_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    existing_question_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
    )

    sequence = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    competency = Column(String(100), nullable=False)
    difficulty = Column(String(50), nullable=False, default="medium")
    progression_stage = Column(String(50), nullable=False, default="practical")  # warmup, fundamental, practical, deep_dive, verification
    expected_signal = Column(Text, nullable=True)
    candidate_evidence_tested = Column(Text, nullable=True)
    job_requirement_tested = Column(Text, nullable=True)
    suggested_followups = Column(JSON, nullable=False, default=list)
    is_ai_generated = Column(Boolean, nullable=False, default=True)

    question_plan = relationship("QuestionPlan", back_populates="items")

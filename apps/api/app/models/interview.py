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


class InterviewType(str, enum.Enum):
    TECHNICAL = "technical"
    CODING = "coding"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"
    MIXED = "mixed"
    SCREENING = "screening"
    CUSTOM = "custom"


class InterviewStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InterviewDifficulty(str, enum.Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


class RoundType(str, enum.Enum):
    TECHNICAL = "technical"
    CODING = "coding"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"
    SCREENING = "screening"
    CUSTOM = "custom"


class QuestionType(str, enum.Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    CONCEPTUAL = "conceptual"
    SITUATIONAL = "situational"


class QuestionDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ParticipantRole(str, enum.Enum):
    INTERVIEWER = "interviewer"
    LEAD_INTERVIEWER = "lead_interviewer"
    OBSERVER = "observer"
    RECRUITER = "recruiter"


class Interview(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """An interview configuration and lifecycle session scoped to a workspace."""

    __tablename__ = "interviews"
    __table_args__ = (
        Index("ix_interviews_workspace_status", "workspace_id", "status"),
        Index("ix_interviews_candidate_id", "candidate_id"),
        Index("ix_interviews_job_id", "job_id"),
    )

    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
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
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    interview_type = Column(
        Enum(InterviewType, native_enum=False),
        nullable=False,
        default=InterviewType.TECHNICAL,
    )
    status = Column(
        Enum(InterviewStatus, native_enum=False),
        nullable=False,
        default=InterviewStatus.DRAFT,
        index=True,
    )
    difficulty = Column(
        Enum(InterviewDifficulty, native_enum=False),
        nullable=False,
        default=InterviewDifficulty.MID,
    )
    duration_minutes = Column(Integer, nullable=False, default=60)
    timezone = Column(String(50), nullable=False, default="UTC")

    instructions = Column(Text, nullable=True)
    candidate_instructions = Column(Text, nullable=True)
    interviewer_instructions = Column(Text, nullable=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="interviews")
    job = relationship("Job", lazy="selectin")
    candidate = relationship("Candidate", lazy="selectin")
    creator = relationship("User", lazy="selectin")
    template = relationship("InterviewTemplate")

    rounds = relationship(
        "InterviewRound",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewRound.sequence",
        lazy="selectin",
    )
    participants = relationship(
        "InterviewParticipant",
        back_populates="interview",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    schedules = relationship(
        "InterviewSchedule",
        back_populates="interview",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    invitations = relationship(
        "InterviewInvitation",
        back_populates="interview",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sessions = relationship(
        "InterviewSession",
        back_populates="interview",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InterviewRound(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """An ordered stage within an interview."""

    __tablename__ = "interview_rounds"
    __table_args__ = (
        UniqueConstraint("interview_id", "sequence", name="uq_interview_round_sequence"),
        Index("ix_interview_rounds_interview_seq", "interview_id", "sequence"),
    )

    interview_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    round_type = Column(
        Enum(RoundType, native_enum=False),
        nullable=False,
        default=RoundType.TECHNICAL,
    )
    sequence = Column(Integer, nullable=False, default=1)
    duration_minutes = Column(Integer, nullable=False, default=30)
    difficulty = Column(
        Enum(InterviewDifficulty, native_enum=False),
        nullable=False,
        default=InterviewDifficulty.MID,
    )
    instructions = Column(Text, nullable=True)
    is_required = Column(Boolean, nullable=False, default=True)
    configuration = Column(JSON, nullable=False, default=dict)

    # Relationships
    interview = relationship("Interview", back_populates="rounds")
    round_questions = relationship(
        "InterviewRoundQuestion",
        back_populates="round",
        cascade="all, delete-orphan",
        order_by="InterviewRoundQuestion.sequence",
        lazy="selectin",
    )


class Question(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A technical, behavioral, or system design question in the question bank."""

    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_workspace_type", "workspace_id", "question_type"),
        Index("ix_questions_category", "category"),
    )

    # Workspace scoped. If workspace_id is NULL, it is a system-wide default question.
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    question_type = Column(
        Enum(QuestionType, native_enum=False),
        nullable=False,
        default=QuestionType.TECHNICAL,
    )
    difficulty = Column(
        Enum(QuestionDifficulty, native_enum=False),
        nullable=False,
        default=QuestionDifficulty.MEDIUM,
    )
    category = Column(String(100), nullable=False, default="General")
    expected_duration_minutes = Column(Integer, nullable=False, default=15)

    skills = Column(JSON, nullable=False, default=list)
    topics = Column(JSON, nullable=False, default=list)
    evaluation_criteria = Column(JSON, nullable=False, default=list)
    hints = Column(JSON, nullable=False, default=list)
    reference_answer = Column(Text, nullable=True)
    is_template = Column(Boolean, nullable=False, default=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="questions")
    creator = relationship("User")


class InterviewRoundQuestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """M2M mapping connecting questions to interview rounds."""

    __tablename__ = "interview_round_questions"
    __table_args__ = (
        UniqueConstraint("round_id", "question_id", name="uq_round_question"),
        UniqueConstraint("round_id", "sequence", name="uq_round_question_seq"),
    )

    round_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence = Column(Integer, nullable=False, default=1)
    is_required = Column(Boolean, nullable=False, default=True)
    time_limit_seconds = Column(Integer, nullable=True)
    configuration = Column(JSON, nullable=False, default=dict)

    # Relationships
    round = relationship("InterviewRound", back_populates="round_questions")
    question = relationship("Question", lazy="selectin")


class InterviewParticipant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Interviewer, lead interviewer, or observer panel member for an interview."""

    __tablename__ = "interview_participants"
    __table_args__ = (
        UniqueConstraint("interview_id", "user_id", name="uq_interview_participant"),
    )

    interview_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_role = Column(
        Enum(ParticipantRole, native_enum=False),
        nullable=False,
        default=ParticipantRole.INTERVIEWER,
    )
    is_primary = Column(Boolean, nullable=False, default=False)

    # Relationships
    interview = relationship("Interview", back_populates="participants")
    user = relationship("User", lazy="selectin")


class InterviewTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Reusable template for rapid interview generation."""

    __tablename__ = "interview_templates"
    __table_args__ = (
        Index("ix_interview_templates_workspace", "workspace_id"),
    )

    # Workspace-scoped; if NULL, represents a system global template
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    interview_type = Column(
        Enum(InterviewType, native_enum=False),
        nullable=False,
        default=InterviewType.TECHNICAL,
    )
    difficulty = Column(
        Enum(InterviewDifficulty, native_enum=False),
        nullable=False,
        default=InterviewDifficulty.MID,
    )
    total_duration_minutes = Column(Integer, nullable=False, default=60)
    is_system = Column(Boolean, nullable=False, default=False)
    configuration = Column(JSON, nullable=False, default=dict)

    # Relationships
    workspace = relationship("Workspace", back_populates="interview_templates")
    creator = relationship("User")
    template_rounds = relationship(
        "InterviewTemplateRound",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="InterviewTemplateRound.sequence",
        lazy="selectin",
    )


class InterviewTemplateRound(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pre-configured round template."""

    __tablename__ = "interview_template_rounds"
    __table_args__ = (
        UniqueConstraint("template_id", "sequence", name="uq_template_round_sequence"),
    )

    template_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    round_type = Column(
        Enum(RoundType, native_enum=False),
        nullable=False,
        default=RoundType.TECHNICAL,
    )
    sequence = Column(Integer, nullable=False, default=1)
    duration_minutes = Column(Integer, nullable=False, default=30)
    difficulty = Column(
        Enum(InterviewDifficulty, native_enum=False),
        nullable=False,
        default=InterviewDifficulty.MID,
    )
    instructions = Column(Text, nullable=True)
    configuration = Column(JSON, nullable=False, default=dict)

    # Relationships
    template = relationship("InterviewTemplate", back_populates="template_rounds")
    template_questions = relationship(
        "InterviewTemplateQuestion",
        back_populates="template_round",
        cascade="all, delete-orphan",
        order_by="InterviewTemplateQuestion.sequence",
        lazy="selectin",
    )


class InterviewTemplateQuestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pre-selected questions for a template round."""

    __tablename__ = "interview_template_questions"
    __table_args__ = (
        UniqueConstraint("template_round_id", "question_id", name="uq_template_round_question"),
    )

    template_round_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_template_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence = Column(Integer, nullable=False, default=1)

    template_round = relationship("InterviewTemplateRound", back_populates="template_questions")
    question = relationship("Question", lazy="selectin")

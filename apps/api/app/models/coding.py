import enum
import uuid
import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
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


class CodingSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class CodingSnapshotReason(str, enum.Enum):
    SESSION_START = "session_start"
    PERIODIC = "periodic"
    MANUAL = "manual"
    BEFORE_EXECUTION = "before_execution"
    SUBMISSION = "submission"
    SESSION_END = "session_end"


class ExecutionJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ExecutionResultStatus(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    COMPILE_ERROR = "compile_error"
    RUNTIME_ERROR = "runtime_error"
    TIMED_OUT = "timed_out"
    MEMORY_EXCEEDED = "memory_exceeded"
    CANCELLED = "cancelled"


class CodingProblemDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CodingProblemStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SubmissionStatus(str, enum.Enum):
    EVALUATING = "evaluating"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    RUNTIME_ERROR = "runtime_error"
    COMPILE_ERROR = "compile_error"


class SessionProblemStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CodingProblem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a reusable coding problem in the library (system or workspace scoped)."""

    __tablename__ = "coding_problems"
    __table_args__ = (
        Index("ix_coding_problems_workspace_id", "workspace_id"),
        Index("ix_coding_problems_difficulty", "difficulty"),
        Index("ix_coding_problems_category", "category"),
        Index("ix_coding_problems_status", "status"),
        Index("ix_coding_problems_is_system", "is_system"),
    )

    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    short_description = Column(Text, nullable=False, default="")
    difficulty = Column(
        Enum(CodingProblemDifficulty, native_enum=False),
        nullable=False,
        default=CodingProblemDifficulty.MEDIUM,
    )
    category = Column(String(64), nullable=False, default="algorithms")
    status = Column(
        Enum(CodingProblemStatus, native_enum=False),
        nullable=False,
        default=CodingProblemStatus.PUBLISHED,
    )
    estimated_duration_minutes = Column(Integer, nullable=False, default=30)
    default_time_limit_seconds = Column(Float, nullable=False, default=5.0)
    default_memory_limit_mb = Column(Integer, nullable=False, default=256)
    tags = Column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    is_system = Column(Boolean, nullable=False, default=False)
    current_version_id = Column(sa.Uuid(as_uuid=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace = relationship("Workspace")
    creator = relationship("User")
    versions = relationship(
        "CodingProblemVersion",
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="CodingProblemVersion.version_number.desc()",
        lazy="selectin",
    )


class CodingProblemVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an immutable version/checkpoint of a coding problem assessment."""

    __tablename__ = "coding_problem_versions"
    __table_args__ = (
        Index("ix_coding_problem_versions_problem_id", "problem_id"),
        UniqueConstraint("problem_id", "version_number", name="uq_problem_version_number"),
    )

    problem_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False, default=1)
    problem_statement = Column(Text, nullable=False, default="")
    examples = Column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    constraints = Column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    expected_time_complexity = Column(String(64), nullable=True)
    expected_space_complexity = Column(String(64), nullable=True)
    starter_codes = Column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    solution_templates = Column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
    )
    scoring_policy = Column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=lambda: {"public_test_weight": 0.2, "hidden_test_weight": 0.8},
    )
    time_limit_seconds = Column(Float, nullable=False, default=5.0)
    memory_limit_mb = Column(Integer, nullable=False, default=256)
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    problem = relationship("CodingProblem", back_populates="versions")
    test_cases = relationship(
        "CodingTestCase",
        back_populates="problem_version",
        cascade="all, delete-orphan",
        order_by="CodingTestCase.order",
        lazy="selectin",
    )


class CodingSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a collaborative coding session attached to an InterviewSession."""

    __tablename__ = "coding_sessions"
    __table_args__ = (
        Index("ix_coding_sessions_interview_session_id", "interview_session_id", unique=True),
        Index("ix_coding_sessions_workspace_id", "workspace_id"),
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
    problem_id = Column(sa.Uuid(as_uuid=True), nullable=True)
    active_problem_version_id = Column(sa.Uuid(as_uuid=True), nullable=True)
    language = Column(String(32), nullable=False, default="python")
    active_file_id = Column(sa.Uuid(as_uuid=True), nullable=True)
    status = Column(
        Enum(CodingSessionStatus, native_enum=False),
        nullable=False,
        default=CodingSessionStatus.ACTIVE,
    )
    is_editor_locked = Column(Boolean, nullable=False, default=False)
    settings_json = Column(
        "settings",
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    # Relationships
    interview_session = relationship("InterviewSession", backref="coding_session")
    files = relationship(
        "CodingFile",
        back_populates="coding_session",
        cascade="all, delete-orphan",
        order_by="CodingFile.created_at",
        lazy="selectin",
    )
    snapshots = relationship(
        "CodingSnapshot",
        back_populates="coding_session",
        cascade="all, delete-orphan",
        order_by="CodingSnapshot.created_at.desc()",
        lazy="selectin",
    )
    test_cases = relationship(
        "CodingTestCase",
        back_populates="coding_session",
        cascade="all, delete-orphan",
        order_by="CodingTestCase.created_at",
        lazy="selectin",
    )
    execution_jobs = relationship(
        "CodingExecutionJob",
        back_populates="coding_session",
        cascade="all, delete-orphan",
        order_by="CodingExecutionJob.created_at.desc()",
        lazy="selectin",
    )
    session_problems = relationship(
        "CodingSessionProblem",
        back_populates="coding_session",
        cascade="all, delete-orphan",
        order_by="CodingSessionProblem.order",
        lazy="selectin",
    )
    submissions = relationship(
        "CodingSubmission",
        back_populates="coding_session",
        cascade="all, delete-orphan",
        order_by="CodingSubmission.submitted_at.desc()",
        lazy="selectin",
    )
    assessments = relationship(
        "CodingAssessment",
        back_populates="coding_session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CodingSessionProblem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an assigned problem within an interview coding session."""

    __tablename__ = "coding_session_problems"
    __table_args__ = (
        Index("ix_coding_session_problems_session_id", "coding_session_id"),
        Index("ix_coding_session_problems_version_id", "problem_version_id"),
    )

    coding_session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_version_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_problem_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    order = Column(Integer, nullable=False, default=1)
    assigned_at = Column(DateTime(timezone=True), nullable=False)
    assigned_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(SessionProblemStatus, native_enum=False),
        nullable=False,
        default=SessionProblemStatus.ASSIGNED,
    )
    score = Column(Float, nullable=False, default=0.0)

    # Relationships
    coding_session = relationship("CodingSession", back_populates="session_problems")
    problem_version = relationship("CodingProblemVersion", lazy="selectin")
    assigner = relationship("User")


class CodingFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a virtual project file in a collaborative coding session."""

    __tablename__ = "coding_files"
    __table_args__ = (
        Index("ix_coding_files_coding_session_id", "coding_session_id"),
        UniqueConstraint("coding_session_id", "path", name="uq_coding_file_session_path"),
    )

    coding_session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    path = Column(String(255), nullable=False)
    name = Column(String(128), nullable=False)
    language = Column(String(32), nullable=False, default="python")
    content = Column(Text, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=False)

    # Relationship
    coding_session = relationship("CodingSession", back_populates="files")


class CodingSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an immutable workspace checkpoint/snapshot of all files at a point in time."""

    __tablename__ = "coding_snapshots"
    __table_args__ = (
        Index("ix_coding_snapshots_coding_session_id", "coding_session_id"),
        Index("ix_coding_snapshots_created_at", "created_at"),
    )

    coding_session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason = Column(
        Enum(CodingSnapshotReason, native_enum=False),
        nullable=False,
        default=CodingSnapshotReason.MANUAL,
    )
    files_json = Column(
        "files",
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )

    # Relationship
    coding_session = relationship("CodingSession", back_populates="snapshots")


class CodingTestCase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a public or hidden test case evaluated during execution/submission."""

    __tablename__ = "coding_test_cases"
    __table_args__ = (
        Index("ix_coding_test_cases_coding_session_id", "coding_session_id"),
        Index("ix_coding_test_cases_problem_version_id", "problem_version_id"),
    )

    coding_session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    problem_version_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_problem_versions.id", ondelete="CASCADE"),
        nullable=True,
    )
    title = Column(String(255), nullable=False)
    input_data = Column(Text, nullable=False, default="")
    expected_output = Column(Text, nullable=False, default="")
    explanation = Column(Text, nullable=False, default="")
    is_hidden = Column(Boolean, nullable=False, default=False)
    weight = Column(Float, nullable=False, default=1.0)
    order = Column(Integer, nullable=False, default=0)
    timeout_seconds = Column(Float, nullable=False, default=5.0)

    # Relationships
    coding_session = relationship("CodingSession", back_populates="test_cases")
    problem_version = relationship("CodingProblemVersion", back_populates="test_cases")


class CodingExecutionJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an asynchronous code execution request enqueued for sandbox processing."""

    __tablename__ = "coding_execution_jobs"
    __table_args__ = (
        Index("ix_coding_execution_jobs_coding_session_id", "coding_session_id"),
        Index("ix_coding_execution_jobs_snapshot_id", "snapshot_id"),
        Index("ix_coding_execution_jobs_status", "status"),
    )

    coding_session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(ExecutionJobStatus, native_enum=False),
        nullable=False,
        default=ExecutionJobStatus.QUEUED,
    )
    language = Column(String(32), nullable=False)
    is_submission = Column(Boolean, nullable=False, default=False)
    custom_input = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    coding_session = relationship("CodingSession", back_populates="execution_jobs")
    snapshot = relationship("CodingSnapshot")
    result = relationship(
        "CodingExecutionResult",
        back_populates="execution_job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CodingExecutionResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents the output and test verdict of an isolated sandbox execution."""

    __tablename__ = "coding_execution_results"
    __table_args__ = (
        Index("ix_coding_execution_results_execution_job_id", "execution_job_id", unique=True),
    )

    execution_job_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_execution_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status = Column(
        Enum(ExecutionResultStatus, native_enum=False),
        nullable=False,
    )
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=False, default="")
    stderr = Column(Text, nullable=False, default="")
    compile_output = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    memory_bytes = Column(BigInteger, nullable=True)
    tests_passed = Column(Integer, nullable=False, default=0)
    tests_failed = Column(Integer, nullable=False, default=0)
    test_results_json = Column(
        "test_results",
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )

    # Relationship
    execution_job = relationship("CodingExecutionJob", back_populates="result")


class CodingSubmission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an immutable candidate solution submission for a problem version."""

    __tablename__ = "coding_submissions"
    __table_args__ = (
        Index("ix_coding_submissions_coding_session_id", "coding_session_id"),
        Index("ix_coding_submissions_problem_version_id", "problem_version_id"),
        Index("ix_coding_submissions_candidate_id", "candidate_id"),
        Index("ix_coding_submissions_status", "status"),
    )

    coding_session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_problem_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_session_problems.id", ondelete="SET NULL"),
        nullable=True,
    )
    problem_version_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_problem_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submission_number = Column(Integer, nullable=False, default=1)
    language = Column(String(32), nullable=False)
    snapshot_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_job_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_execution_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(SubmissionStatus, native_enum=False),
        nullable=False,
        default=SubmissionStatus.EVALUATING,
    )
    score = Column(Float, nullable=False, default=0.0)
    tests_passed = Column(Integer, nullable=False, default=0)
    tests_failed = Column(Integer, nullable=False, default=0)
    total_tests = Column(Integer, nullable=False, default=0)
    runtime_ms = Column(Integer, nullable=False, default=0)
    memory_bytes = Column(BigInteger, nullable=False, default=0)
    submitted_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    coding_session = relationship("CodingSession", back_populates="submissions")
    session_problem = relationship("CodingSessionProblem")
    problem_version = relationship("CodingProblemVersion", lazy="selectin")
    candidate = relationship("User")
    snapshot = relationship("CodingSnapshot", lazy="selectin")
    execution_job = relationship("CodingExecutionJob", lazy="selectin")


class CodingAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Consolidated assessment score and rubric performance for a candidate on a problem."""

    __tablename__ = "coding_assessments"
    __table_args__ = (
        Index("ix_coding_assessments_coding_session_id", "coding_session_id"),
        Index("ix_coding_assessments_problem_version_id", "problem_version_id"),
        Index("ix_coding_assessments_candidate_id", "candidate_id"),
        UniqueConstraint("coding_session_id", "problem_version_id", "candidate_id", name="uq_session_problem_candidate_assessment"),
    )

    coding_session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_version_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("coding_problem_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_submissions = Column(Integer, nullable=False, default=0)
    best_score = Column(Float, nullable=False, default=0.0)
    passed = Column(Boolean, nullable=False, default=False)
    evaluation_summary = Column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    # Relationships
    coding_session = relationship("CodingSession", back_populates="assessments")
    problem_version = relationship("CodingProblemVersion", lazy="selectin")
    candidate = relationship("User")

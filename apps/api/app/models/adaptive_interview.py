"""
Adaptive Interview Models — Phase 14.

Defines database models for:
- Speech-to-Text Transcript Segments with speaker attribution and finality flags
- AI Interview Recommendations (probes, follow-ups, difficulty, coverage shifts) with audit lifecycle
- Real-time Interview Competency Evidence Tracking
"""

import enum
import uuid
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
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class RecommendationAction(str, enum.Enum):
    ASK_APPROVED_QUESTION = "ask_approved_question"
    GENERATE_FOLLOW_UP = "generate_follow_up"
    INCREASE_DIFFICULTY = "increase_difficulty"
    DECREASE_DIFFICULTY = "decrease_difficulty"
    PROBE_WEAK_EVIDENCE = "probe_weak_evidence"
    PROBE_RESUME_CLAIM = "probe_resume_claim"
    MOVE_TO_NEXT_COMPETENCY = "move_to_next_competency"
    REVISIT_COMPETENCY = "revisit_competency"
    SKIP_LOW_VALUE_QUESTION = "skip_low_value_question"
    NO_ACTION = "no_action"


class RecommendationStatus(str, enum.Enum):
    GENERATING = "generating"
    GENERATED = "generated"
    VALIDATED = "validated"
    PRESENTED = "presented"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    SKIPPED = "skipped"
    STALE = "stale"
    EXPIRED = "expired"
    FAILED = "failed"


class EvidenceStrength(str, enum.Enum):
    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class CompetencyStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PARTIAL = "partial"
    COVERED = "covered"
    STRONG = "strong"
    INSUFFICIENT = "insufficient"


class ResponseBoundaryStatus(str, enum.Enum):
    RESPONSE_STARTED = "response_started"
    RESPONSE_CONTINUING = "response_continuing"
    RESPONSE_COMPLETE = "response_complete"
    RESPONSE_INTERRUPTED = "response_interrupted"


class TranscriptSegment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stores speech-to-text transcript segments with speaker attribution."""

    __tablename__ = "transcript_segments"
    __table_args__ = (
        Index("ix_transcript_segments_interview_id", "interview_id"),
        Index("ix_transcript_segments_session_id", "session_id"),
        Index("ix_transcript_segments_workspace_id", "workspace_id"),
        Index("ix_transcript_segments_created_at", "created_at"),
    )

    interview_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    speaker_id = Column(sa.Uuid(as_uuid=True), nullable=True)
    speaker_role = Column(String(32), nullable=False, default="candidate")  # candidate, interviewer, system
    speaker_name = Column(String(100), nullable=True)

    start_time_seconds = Column(Float, nullable=False, default=0.0)
    end_time_seconds = Column(Float, nullable=False, default=0.0)

    text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    is_final = Column(Boolean, nullable=False, default=True)

    detected_topics = Column(
        JSONB().with_variant(sa.JSON, "sqlite"),
        nullable=False,
        default=list,
    )
    metadata_json = Column(
        JSONB().with_variant(sa.JSON, "sqlite"),
        nullable=False,
        default=dict,
    )


class AIInterviewRecommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Authoritative persistent record of an AI-generated interview recommendation."""

    __tablename__ = "ai_interview_recommendations"
    __table_args__ = (
        Index("ix_ai_recs_interview_id", "interview_id"),
        Index("ix_ai_recs_session_id", "session_id"),
        Index("ix_ai_recs_workspace_id", "workspace_id"),
        Index("ix_ai_recs_status", "status"),
        Index("ix_ai_recs_created_at", "created_at"),
    )

    interview_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    action = Column(
        Enum(RecommendationAction, native_enum=False),
        nullable=False,
        default=RecommendationAction.GENERATE_FOLLOW_UP,
    )
    status = Column(
        Enum(RecommendationStatus, native_enum=False),
        nullable=False,
        default=RecommendationStatus.GENERATED,
    )

    # Question payload
    recommended_question = Column(Text, nullable=False)
    original_question = Column(Text, nullable=True)
    edited_question = Column(Text, nullable=True)

    competency = Column(String(100), nullable=True)
    difficulty = Column(String(32), nullable=False, default="medium")  # easy, medium, hard
    reason = Column(Text, nullable=False)
    evidence_target = Column(Text, nullable=True)
    time_cost_estimate_seconds = Column(Integer, nullable=False, default=180)
    confidence = Column(Float, nullable=False, default=0.85)

    source_question_id = Column(sa.Uuid(as_uuid=True), nullable=True)
    source_claim_id = Column(sa.Uuid(as_uuid=True), nullable=True)

    context_revision = Column(Integer, nullable=False, default=1)
    requires_interviewer_approval = Column(Boolean, nullable=False, default=True)

    # Interviewer action tracking
    reviewed_by = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reject_reason = Column(Text, nullable=True)

    metadata_json = Column(
        JSONB().with_variant(sa.JSON, "sqlite"),
        nullable=False,
        default=dict,
    )


class InterviewCompetencyEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks live evidence gathered for each competency throughout the interview session."""

    __tablename__ = "interview_competency_evidence"
    __table_args__ = (
        Index("ix_comp_evidence_interview_id", "interview_id"),
        Index("ix_comp_evidence_session_id", "session_id"),
        Index("ix_comp_evidence_competency", "competency"),
    )

    interview_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    workspace_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    competency = Column(String(100), nullable=False)
    evidence_strength = Column(
        Enum(EvidenceStrength, native_enum=False),
        nullable=False,
        default=EvidenceStrength.NONE,
    )
    status = Column(
        Enum(CompetencyStatus, native_enum=False),
        nullable=False,
        default=CompetencyStatus.NOT_STARTED,
    )

    questions_asked_count = Column(Integer, nullable=False, default=0)
    demonstrated_concepts = Column(
        JSONB().with_variant(sa.JSON, "sqlite"),
        nullable=False,
        default=list,
    )
    missing_concepts = Column(
        JSONB().with_variant(sa.JSON, "sqlite"),
        nullable=False,
        default=list,
    )
    notes = Column(Text, nullable=True)

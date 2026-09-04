"""
Phase 15 — Evidence-Based Evaluation, Scoring & Reporting Models.

Defines:
- Evaluation: Top-level evaluation entity with lifecycle (DRAFT, IN_REVIEW, APPROVED, FINALIZED)
- EvaluationEvidence: Normalized evidence referencing transcripts, code submissions, whiteboard snapshots, resume claims, and notes
- EvaluationCompetencyScore: Per-competency rubric level, calculated score, confidence, strengths, and evidence links
- EvaluationQuestionScore: Question-level evidence mapping and score
- EvaluationContradiction: Contradictions detected across resume, interview responses, and execution results
- EvaluationScoreInput: Persisted score inputs enabling 100% deterministic recalculation and reproducibility
- EvaluationVersion: Immutable historical snapshots of evaluations
- EvaluationAuditEvent: Full audit trail for score overrides, status changes, and finalization
- EvaluationCompetency: Workspace-configurable competencies
- CompetencyRubric: 5-level rubric criteria for each competency
"""

from datetime import datetime, timezone
import enum
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class EvaluationStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    FINALIZED = "finalized"


class HiringRecommendation(str, enum.Enum):
    STRONG_HIRE = "strong_hire"
    HIRE = "hire"
    LEAN_HIRE = "lean_hire"
    LEAN_NO_HIRE = "lean_no_hire"
    NO_HIRE = "no_hire"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceSourceType(str, enum.Enum):
    TRANSCRIPT = "transcript"
    CODING = "coding"
    CODE_EXECUTION = "code_execution"
    WHITEBOARD = "whiteboard"
    CHAT = "chat"
    INTERVIEWER_NOTE = "interviewer_note"
    RESUME_CLAIM = "resume_claim"
    ADAPTIVE_RECOMMENDATION = "adaptive_recommendation"


class ContradictionSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvaluationCompetency(Base):
    """Workspace-level or template-level configurable competency."""

    __tablename__ = "evaluation_competencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, default="technical")  # technical, behavioral, system_design, etc.
    description = Column(Text, nullable=True)
    default_weight = Column(Float, nullable=False, default=1.0)
    is_required = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    rubrics = relationship("CompetencyRubric", back_populates="competency", cascade="all, delete-orphan")


class CompetencyRubric(Base):
    """5-level rubric criteria for a competency."""

    __tablename__ = "competency_rubrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competency_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_competencies.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(Integer, nullable=False)  # 1 (Unsatisfactory) to 5 (Exemplary)
    title = Column(String(100), nullable=False)  # Unsatisfactory, Developing, Competent, Strong, Exemplary
    criteria = Column(Text, nullable=False)
    indicators = Column(JSON, nullable=False, default=list)  # List of positive/negative indicators
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    competency = relationship("EvaluationCompetency", back_populates="rubrics")


class EvaluationEvidence(Base):
    """
    Normalized interview evidence item.
    Links directly to source records (transcript segment, code submission, whiteboard snapshot, resume claim, note).
    """

    __tablename__ = "evaluation_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="SET NULL"), nullable=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)

    source_type = Column(String(50), nullable=False)  # transcript, coding, code_execution, whiteboard, etc.
    source_id = Column(UUID(as_uuid=True), nullable=True)  # ID in source table if applicable
    
    competency_name = Column(String(100), nullable=True, index=True)
    question_text = Column(Text, nullable=True)

    content = Column(Text, nullable=False)
    structured_payload = Column(JSON, nullable=False, default=dict)

    evidence_timestamp_seconds = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, nullable=False, default=1.0)
    confidence = Column(Float, nullable=False, default=1.0)

    is_candidate_evidence = Column(Boolean, nullable=False, default=True)
    is_interviewer_observation = Column(Boolean, nullable=False, default=False)
    
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Evaluation(Base):
    """
    Parent evaluation entity for an interview.
    Tracks overall scores, hiring recommendation, lifecycle status, and immutability locks.
    """

    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)

    status = Column(String(30), nullable=False, default=EvaluationStatus.DRAFT.value)
    version = Column(Integer, nullable=False, default=1)

    # Deterministic Scores
    overall_score = Column(Float, nullable=False, default=0.0)  # 0.0 to 100.0
    overall_rubric_level = Column(Float, nullable=False, default=0.0)  # 1.0 to 5.0
    confidence = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    recommendation = Column(String(50), nullable=False, default=HiringRecommendation.INSUFFICIENT_EVIDENCE.value)
    
    summary = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=False, default=list)  # List of { claim: str, evidence_ids: list[str] }
    development_areas = Column(JSON, nullable=False, default=list)  # List of { claim: str, evidence_ids: list[str] }
    evidence_gaps = Column(JSON, nullable=False, default=list)  # List of { competency: str, reason: str }

    # Human Review Metadata
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    finalized_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    is_locked = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    competency_scores = relationship("EvaluationCompetencyScore", back_populates="evaluation", cascade="all, delete-orphan")
    contradictions = relationship("EvaluationContradiction", back_populates="evaluation", cascade="all, delete-orphan")
    score_inputs = relationship("EvaluationScoreInput", back_populates="evaluation", cascade="all, delete-orphan")
    audit_events = relationship("EvaluationAuditEvent", back_populates="evaluation", cascade="all, delete-orphan")
    versions = relationship("EvaluationVersion", back_populates="evaluation", cascade="all, delete-orphan")


class EvaluationCompetencyScore(Base):
    """Competency evaluation score breakdown linking directly to supporting evidence."""

    __tablename__ = "evaluation_competency_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True)
    competency_name = Column(String(100), nullable=False, index=True)
    
    rubric_level = Column(Float, nullable=False)  # 1.0 to 5.0
    calculated_score = Column(Float, nullable=False)  # 0.0 to 100.0
    weight = Column(Float, nullable=False, default=1.0)
    confidence = Column(Float, nullable=False, default=1.0)
    status = Column(String(50), nullable=False, default="assessed")  # assessed, not_assessed, insufficient_evidence

    rationale = Column(Text, nullable=False)
    observed_facts = Column(JSON, nullable=False, default=list)
    inferences = Column(JSON, nullable=False, default=list)
    evidence_ids = Column(JSON, nullable=False, default=list)  # UUID strings of EvaluationEvidence

    # Human Override Tracking
    is_overridden = Column(Boolean, nullable=False, default=False)
    original_ai_rubric_level = Column(Float, nullable=True)
    override_reason = Column(Text, nullable=True)
    overridden_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    overridden_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    evaluation = relationship("Evaluation", back_populates="competency_scores")


class EvaluationContradiction(Base):
    """Contradiction detected across resume, interview response, and code execution."""

    __tablename__ = "evaluation_contradictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    type = Column(String(50), nullable=False)  # resume_vs_interview, note_vs_execution, claim_vs_whiteboard
    severity = Column(String(30), nullable=False, default=ContradictionSeverity.MEDIUM.value)
    
    source_a_type = Column(String(50), nullable=False)
    source_a_id = Column(UUID(as_uuid=True), nullable=True)
    source_a_description = Column(Text, nullable=False)

    source_b_type = Column(String(50), nullable=False)
    source_b_id = Column(UUID(as_uuid=True), nullable=True)
    source_b_description = Column(Text, nullable=False)

    description = Column(Text, nullable=False)
    resolution = Column(Text, nullable=True)
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    evaluation = relationship("Evaluation", back_populates="contradictions")


class EvaluationScoreInput(Base):
    """
    Persisted deterministic score inputs.
    Guarantees 100% score recalculation and reproducibility without LLMs.
    """

    __tablename__ = "evaluation_score_inputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    scoring_formula = Column(String(100), nullable=False, default="weighted_rubric_average")
    competency_weights = Column(JSON, nullable=False, default=dict)  # { "System Design": 1.5, "Coding": 2.0 }
    competency_rubric_levels = Column(JSON, nullable=False, default=dict)  # { "System Design": 4.0, "Coding": 4.5 }
    calculated_overall_score = Column(Float, nullable=False)
    calculated_recommendation = Column(String(50), nullable=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    evaluation = relationship("Evaluation", back_populates="score_inputs")


class EvaluationVersion(Base):
    """Immutable snapshot of an evaluation at a specific version."""

    __tablename__ = "evaluation_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False)
    
    overall_score = Column(Float, nullable=False)
    recommendation = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    
    snapshot_payload = Column(JSON, nullable=False, default=dict)
    integrity_hash = Column(String(64), nullable=True)  # SHA-256 canonical hash of snapshot_payload
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    evaluation = relationship("Evaluation", back_populates="versions")


class EvaluationAuditEvent(Base):
    """Audit event for all human and system evaluation mutations."""

    __tablename__ = "evaluation_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    action = Column(String(100), nullable=False)  # score_overridden, evaluation_approved, evaluation_finalized, etc.
    before_state = Column(JSON, nullable=False, default=dict)
    after_state = Column(JSON, nullable=False, default=dict)
    rationale = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    evaluation = relationship("Evaluation", back_populates="audit_events")

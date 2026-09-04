"""
Pydantic Schemas for Phase 15 AI Evaluation & Report Generation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GroundingStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class GroundedClaim(BaseModel):
    claim_id: str = Field(default_factory=lambda: "")
    claim_text: str = ""
    evidence_ids: List[str] = Field(default_factory=list)
    grounding_status: GroundingStatus = GroundingStatus.SUPPORTED
    grounding_reason: str = ""
    is_quote: bool = False
    verified_quote: bool = False


class QuoteVerificationResult(BaseModel):
    quote_text: str
    speaker_role: str = "candidate"
    is_verified: bool = False
    matching_evidence_id: Optional[str] = None
    similarity_score: float = 0.0
    rejection_reason: Optional[str] = None


class CompetencyAssessmentInput(BaseModel):
    competency_name: str
    category: str = "technical"
    default_weight: float = 1.0
    is_required: bool = False
    evidence_texts: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class CompetencyEvaluationOutput(BaseModel):
    competency_name: str
    rubric_level: float = Field(..., ge=1.0, le=5.0, description="1.0 Unsatisfactory to 5.0 Exemplary")
    weight: float = Field(default=1.0)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    status: str = Field(default="assessed", description="assessed, not_assessed, insufficient_evidence")
    rationale: str = ""
    observed_facts: List[str] = Field(default_factory=list)
    inferences: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


class EvidenceAnalysisOutput(BaseModel):
    key_themes: List[str] = Field(default_factory=list)
    technical_signals: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.9)
    unsupported_claims: List[str] = Field(default_factory=list)


class CodingEvaluationOutput(BaseModel):
    competency_name: str = "Coding & Problem Solving"
    rubric_level: float = 4.0
    confidence: float = 0.95
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    correctness_score: float = 90.0
    code_quality_score: float = 85.0
    algorithmic_efficiency_score: float = 90.0


class ContradictionItem(BaseModel):
    category: str = "resume_vs_performance"
    severity: str = "medium"  # low, medium, high, critical
    claim: str = ""
    observed_evidence: str = ""
    explanation: str = ""
    evidence_ids: List[str] = Field(default_factory=list)


class ContradictionDetectionOutput(BaseModel):
    contradictions: List[ContradictionItem] = Field(default_factory=list)
    unverified_claims: List[str] = Field(default_factory=list)
    integrity_score: float = 100.0


class EvaluationSynthesisOutput(BaseModel):
    executive_summary: str = ""
    overall_recommendation: str = "STRONG_HIRE"
    hiring_confidence: float = 0.95
    key_strengths: List[str] = Field(default_factory=list)
    key_weaknesses: List[str] = Field(default_factory=list)
    recommended_level: str = "Senior Engineer"
    risk_factors: List[str] = Field(default_factory=list)


class ContradictionOutput(BaseModel):
    type: str = "resume_vs_interview"
    severity: str = "medium"  # low, medium, high, critical
    source_a_type: str = "resume_claim"
    source_a_description: str = ""
    source_b_type: str = "interview_response"
    source_b_description: str = ""
    description: str = ""


class StrengthItem(BaseModel):
    claim: str
    evidence_ids: List[str] = Field(default_factory=list)


class DevelopmentAreaItem(BaseModel):
    claim: str
    evidence_ids: List[str] = Field(default_factory=list)


class EvidenceGapItem(BaseModel):
    competency: str
    reason: str


class EvaluationReportOutput(BaseModel):
    summary: str
    competency_evaluations: List[CompetencyEvaluationOutput] = Field(default_factory=list)
    strengths: List[StrengthItem] = Field(default_factory=list)
    development_areas: List[DevelopmentAreaItem] = Field(default_factory=list)
    evidence_gaps: List[EvidenceGapItem] = Field(default_factory=list)
    contradictions: List[ContradictionOutput] = Field(default_factory=list)
    grounded_claims: List[GroundedClaim] = Field(default_factory=list)
    quote_verifications: List[QuoteVerificationResult] = Field(default_factory=list)

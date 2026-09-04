"""AI schema for Personalized Question Planning."""

from typing import List, Optional
from pydantic import BaseModel, Field


class QuestionPlanItemRecommendation(BaseModel):
    sequence: int = Field(default=1, ge=1, le=20)
    title: str = Field(..., min_length=5, max_length=150)
    prompt: str = Field(..., min_length=15, max_length=1000)
    competency: str = Field(..., min_length=2, max_length=80)
    difficulty: str = "medium"  # easy, medium, hard
    progression_stage: str = "practical"  # warmup, fundamental, practical, deep_dive, verification
    expected_signal: Optional[str] = None
    candidate_evidence_tested: Optional[str] = None
    job_requirement_tested: Optional[str] = None
    suggested_followups: List[str] = Field(default_factory=list, max_length=5)


class QuestionPlanAnalysis(BaseModel):
    """Output of Question Planning Agent."""

    title: str = Field(..., min_length=5, max_length=150)
    target_competencies: List[str] = Field(default_factory=list, max_length=10)
    questions: List[QuestionPlanItemRecommendation] = Field(default_factory=list, max_length=15)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, max_length=10)

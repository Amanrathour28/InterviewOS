"""
Adaptive Interview Schemas — Phase 14.

Pydantic schemas for structured LLM outputs:
- Response analysis and evidence extraction
- Bounded difficulty adaptation
- Competency coverage updates
- Adaptive interview recommendations and pacing strategy
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ResponseAnalysisOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    completeness_score: float = Field(default=0.8, description="Completeness score 0.0 to 1.0")
    demonstrated_concepts: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    evidence_strength: str = Field(default="moderate", description="none, weak, moderate, strong")
    suggested_probe_angles: List[str] = Field(default_factory=list)
    key_claims_mentioned: List[str] = Field(default_factory=list)
    summary: str = Field(default="")


class DifficultyAdaptationOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_difficulty: str = Field(default="medium")
    recommended_difficulty: str = Field(default="medium")
    adjustment_direction: str = Field(default="maintain", description="increase, decrease, maintain")
    rationale: str = Field(default="")
    confidence: float = Field(default=0.85)


class CompetencyCoverageOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    competency: str
    status: str = Field(default="partial", description="not_started, partial, covered, strong, insufficient")
    evidence_strength: str = Field(default="moderate")
    demonstrated_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    reasoning: str = Field(default="")


class AdaptiveRecommendationOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: str = Field(
        default="generate_follow_up",
        description="ask_approved_question, generate_follow_up, increase_difficulty, decrease_difficulty, probe_weak_evidence, probe_resume_claim, move_to_next_competency, revisit_competency, skip_low_value_question, no_action",
    )
    recommended_question: str = Field(..., description="Target question text recommended to the interviewer")
    competency: str = Field(default="General", description="Competency targeted")
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    reason: str = Field(..., description="Concise explanation for the recommendation")
    evidence_target: str = Field(default="", description="Target signal or skill expected in response")
    time_cost_estimate_seconds: int = Field(default=180, description="Estimated time needed in seconds")
    confidence: float = Field(default=0.85, description="Confidence score 0.0 to 1.0")
    source_question_id: Optional[str] = Field(default=None)
    requires_approval: bool = Field(default=True, description="Always true for human-in-the-loop")


class InterviewStrategyOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pacing_status: str = Field(default="on_track", description="ahead, on_track, behind, critical")
    recommended_action: str = Field(default="generate_follow_up")
    priority_competency: str = Field(default="")
    rationale: str = Field(default="")
    estimated_remaining_questions: int = Field(default=3)

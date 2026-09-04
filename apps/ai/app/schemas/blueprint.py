"""AI schema for Interview Blueprint Recommendations."""

from typing import List, Optional
from pydantic import BaseModel, Field


class BlueprintRoundRecommendation(BaseModel):
    name: str
    round_type: str = "technical"  # technical, coding, system_design, behavioral, screening
    sequence: int = Field(default=1, ge=1, le=10)
    duration_minutes: int = Field(default=30, ge=15, le=120)
    difficulty: str = "mid"  # entry, mid, senior, lead, principal
    objectives: List[str] = Field(default_factory=list, max_length=5)
    competencies: List[str] = Field(default_factory=list, max_length=6)
    topics: List[str] = Field(default_factory=list, max_length=8)
    suggested_question_count: int = Field(default=3, ge=1, le=10)
    scoring_weight: float = Field(default=1.0, ge=0.1, le=5.0)


class InterviewBlueprintAnalysis(BaseModel):
    """Output of Interview Planning Agent generating interview structures."""

    title: str = Field(..., min_length=5, max_length=150)
    total_duration_minutes: int = Field(default=60, ge=15, le=300)
    target_seniority: str = "mid"
    candidate_focus_areas: List[str] = Field(default_factory=list, max_length=8)
    job_focus_areas: List[str] = Field(default_factory=list, max_length=8)
    verification_priorities: List[str] = Field(default_factory=list, max_length=8)
    rounds: List[BlueprintRoundRecommendation] = Field(default_factory=list, max_length=8)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, max_length=10)

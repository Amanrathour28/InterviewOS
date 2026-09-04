"""AI schema for Candidate-Job Matching Explanation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MatchStrength(BaseModel):
    skill: str
    category: str = "general"
    importance: str = "required"
    evidence: str
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class MatchGap(BaseModel):
    skill: str
    category: str = "general"
    importance: str = "required"
    reason: str


class MatchVerificationArea(BaseModel):
    topic: str
    reason: str
    suggested_probes: List[str] = Field(default_factory=list)


class CandidateJobMatchAnalysis(BaseModel):
    """Output of AI Matching Agent explaining deterministic match results."""

    strengths: List[MatchStrength] = Field(default_factory=list, max_length=15)
    gaps: List[MatchGap] = Field(default_factory=list, max_length=15)
    verification_areas: List[MatchVerificationArea] = Field(default_factory=list, max_length=10)
    summary_explanation: str = Field(..., min_length=20, max_length=1200)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, max_length=10)

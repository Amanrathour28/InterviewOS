"""Agent output schemas for job description intelligence."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SkillRequirement(BaseModel):
    skill: str
    level: Literal["required", "preferred"]
    weight: float = Field(default=1.0, ge=0.0, le=3.0)


class JDAnalysis(BaseModel):
    """
    Output of the JD Intelligence Agent.
    Extracts structured interview priorities from a job description.
    """

    # Extracted job metadata
    seniority: Literal["entry", "mid", "senior", "lead", "principal", "unknown"]
    technical_domains: List[str] = Field(default_factory=list, max_length=10)

    # Skills taxonomy
    required_skills: List[SkillRequirement] = Field(default_factory=list, max_length=20)
    preferred_skills: List[SkillRequirement] = Field(default_factory=list, max_length=15)

    # Interview planning
    interview_focus: List[str] = Field(default_factory=list, max_length=8)
    suggested_rounds: List[str] = Field(default_factory=list, max_length=5)
    question_topics: List[str] = Field(default_factory=list, max_length=15)

    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, max_length=8)

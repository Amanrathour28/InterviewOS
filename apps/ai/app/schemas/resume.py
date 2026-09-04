"""Agent output schemas for resume intelligence."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResumeSkill(BaseModel):
    name: str
    proficiency: Optional[str] = None  # "expert" | "proficient" | "familiar" | unknown
    years_of_experience: Optional[float] = None
    evidence: Optional[str] = None  # Direct quote or reference from resume


class ResumeProject(BaseModel):
    title: str
    description: str
    technologies: List[str] = Field(default_factory=list)
    suggested_question: Optional[str] = None


class ResumeClaimItem(BaseModel):
    claim: str
    category: str = "general"
    status: str = "explicit"  # explicit, inferred, unverified
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    verification_priority: str = "medium"  # high, medium, low
    evidence: Dict[str, Any] = Field(default_factory=dict)  # {source, page, text}
    suggested_probes: List[str] = Field(default_factory=list)


class ResumeAnalysis(BaseModel):
    """
    Output of the Resume Intelligence Agent.
    All claims must reference evidence from the actual resume.
    """

    candidate_summary: str = Field(..., min_length=20, max_length=800)

    # Extracted data
    skills: List[ResumeSkill] = Field(default_factory=list, max_length=30)
    technologies: List[str] = Field(default_factory=list, max_length=30)
    experience_years: Optional[float] = None
    notable_projects: List[ResumeProject] = Field(default_factory=list, max_length=5)

    # Claims with provenance
    claims: List[ResumeClaimItem] = Field(default_factory=list, max_length=20)

    # Interview guidance
    technical_areas_to_probe: List[str] = Field(default_factory=list, max_length=8)
    project_specific_questions: List[str] = Field(default_factory=list, max_length=5)
    potential_inconsistencies: List[str] = Field(default_factory=list, max_length=3)

    # Overall confidence
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, max_length=10)

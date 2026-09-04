"""Agent output schemas for system design analysis."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ArchitectureComponent(BaseModel):
    name: str
    role: Optional[str] = None
    present_on_whiteboard: bool = True


class SystemDesignAnalysis(BaseModel):
    """
    Output of the System Design Analysis Agent.

    Confidence should reflect that visual inference from whiteboard state
    is inherently imprecise. Include evidence to ground all claims.
    """

    architecture_summary: str = Field(..., min_length=10, max_length=600)

    # Identified components
    identified_components: List[ArchitectureComponent] = Field(default_factory=list, max_length=15)
    missing_components: List[str] = Field(default_factory=list, max_length=6)

    # Design observations
    scalability_observations: List[str] = Field(default_factory=list, max_length=5)
    bottlenecks: List[str] = Field(default_factory=list, max_length=4)
    reliability_concerns: List[str] = Field(default_factory=list, max_length=4)
    consistency_tradeoffs: List[str] = Field(default_factory=list, max_length=4)

    # Suggested follow-up questions
    suggested_follow_ups: List[str] = Field(default_factory=list, max_length=4)

    # Confidence is explicitly shown because whiteboard inference is limited
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, max_length=8)

    # Explicit inference limitation note
    inference_note: str = Field(
        default="Visual inference from whiteboard state is limited. Confidence reflects this uncertainty."
    )

"""Agent output schemas for coding analysis."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class CodeBug(BaseModel):
    description: str
    line_hint: Optional[str] = None  # "around line X" — never a definitive assertion
    severity: Literal["critical", "major", "minor", "style"]


class CodingAnalysis(BaseModel):
    """
    Output of the Coding Analysis Agent.

    IMPORTANT INVARIANT: This agent NEVER overrides or modifies actual sandbox execution results.
    Deterministic test results from the Docker sandbox remain authoritative.
    This analysis provides reasoning and explanation — not verdicts.
    """

    # Approach summary
    approach_summary: str = Field(..., min_length=10, max_length=600)

    # Complexity estimates (AI inference — may be imprecise)
    time_complexity_estimate: Optional[str] = None  # e.g. "O(n log n)"
    space_complexity_estimate: Optional[str] = None

    # Observations
    correctness_observations: List[str] = Field(default_factory=list, max_length=6)
    potential_bugs: List[CodeBug] = Field(default_factory=list, max_length=5)
    edge_case_observations: List[str] = Field(default_factory=list, max_length=5)
    code_quality_observations: List[str] = Field(default_factory=list, max_length=5)
    improvement_suggestions: List[str] = Field(default_factory=list, max_length=4)

    # Suggested follow-up questions
    suggested_follow_ups: List[str] = Field(default_factory=list, max_length=3)

    # Confidence + evidence from actual submission data
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list, max_length=6)

    # Explicit disclaimer that this does not override sandbox results
    disclaimer: str = Field(
        default="AI analysis is advisory. Sandbox execution results are authoritative."
    )

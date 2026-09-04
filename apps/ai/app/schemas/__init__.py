"""Schemas package init."""

from app.schemas.question import GeneratedQuestion, FollowUpSuggestion
from app.schemas.resume import ResumeAnalysis, ResumeClaimItem, ResumeSkill, ResumeProject
from app.schemas.jd import JDAnalysis, SkillRequirement
from app.schemas.coding import CodingAnalysis
from app.schemas.system_design import SystemDesignAnalysis
from app.schemas.matching import CandidateJobMatchAnalysis, MatchStrength, MatchGap, MatchVerificationArea
from app.schemas.blueprint import InterviewBlueprintAnalysis, BlueprintRoundRecommendation
from app.schemas.question_plan import QuestionPlanAnalysis, QuestionPlanItemRecommendation

__all__ = [
    "GeneratedQuestion",
    "FollowUpSuggestion",
    "ResumeAnalysis",
    "ResumeClaimItem",
    "ResumeSkill",
    "ResumeProject",
    "JDAnalysis",
    "SkillRequirement",
    "CodingAnalysis",
    "SystemDesignAnalysis",
    "CandidateJobMatchAnalysis",
    "MatchStrength",
    "MatchGap",
    "MatchVerificationArea",
    "InterviewBlueprintAnalysis",
    "BlueprintRoundRecommendation",
    "QuestionPlanAnalysis",
    "QuestionPlanItemRecommendation",
]

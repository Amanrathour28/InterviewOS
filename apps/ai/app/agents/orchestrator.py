"""
Interview Orchestrator Agent.

Routes AI tasks to the appropriate specialized agent.
Does NOT autonomously control interviews.
Does NOT ask questions to candidates.
Does NOT change interview stage.

Routing map:
  "question_generation"    → QuestionGenerationAgent
  "follow_up"              → FollowUpAgent
  "resume_analysis"        → ResumeAgent
  "jd_analysis"            → JDAgent
  "coding_analysis"        → CodingAnalysisAgent
  "system_design_analysis" → SystemDesignAgent
  "candidate_job_matching" → MatchingAgent
  "interview_blueprint"    → InterviewPlanningAgent
  "question_plan"          → QuestionPlanningAgent
"""

import logging
from typing import Optional

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.coding_agent import CodingAnalysisAgent
from app.agents.followup_agent import FollowUpAgent
from app.agents.jd_agent import JDAgent
from app.agents.matching_agent import MatchingAgent
from app.agents.blueprint_agent import InterviewPlanningAgent
from app.agents.question_planner_agent import QuestionPlanningAgent
from app.agents.question_agent import QuestionGenerationAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.system_design_agent import SystemDesignAgent
from app.agents.response_analysis_agent import ResponseAnalysisAgent
from app.agents.difficulty_agent import DifficultyAgent
from app.agents.coverage_agent import CoverageAgent
from app.agents.adaptive_interview_agent import AdaptiveInterviewAgent
from app.gateway.ai_gateway import AIGateway

logger = logging.getLogger("interviewos.ai.agents.orchestrator")

# Task type → agent class mapping
_AGENT_REGISTRY = {
    "question_generation": QuestionGenerationAgent,
    "follow_up": FollowUpAgent,
    "resume_analysis": ResumeAgent,
    "jd_analysis": JDAgent,
    "coding_analysis": CodingAnalysisAgent,
    "system_design_analysis": SystemDesignAgent,
    "candidate_job_matching": MatchingAgent,
    "interview_blueprint": InterviewPlanningAgent,
    "question_plan": QuestionPlanningAgent,
    "response_analysis": ResponseAnalysisAgent,
    "difficulty_adaptation": DifficultyAgent,
    "coverage_analysis": CoverageAgent,
    "adaptive_interview": AdaptiveInterviewAgent,
}


class OrchestratorAgent(BaseAgent):
    """
    Routes AI tasks to specialized agents.
    Not yet capable of autonomous interview control — Phase 14+ scope.
    """

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "orchestrator"

    async def run(self, ctx: AgentContext) -> AgentResult:
        task_type = ctx.extra.get("task_type")

        if not task_type:
            return self._build_error_result(
                ctx, ValueError("task_type is required in ctx.extra")
            )

        agent_class = _AGENT_REGISTRY.get(task_type)
        if not agent_class:
            return self._build_error_result(
                ctx,
                ValueError(
                    f"Unknown task type: {task_type!r}. "
                    f"Valid types: {list(_AGENT_REGISTRY.keys())}"
                ),
            )

        logger.info(
            "Orchestrator routing task_type=%s to %s (session=%s)",
            task_type, agent_class.__name__, ctx.session_id,
        )

        agent = agent_class(gateway=self.gateway)
        return await agent.run(ctx)


def get_available_tasks() -> list:
    """Return the list of supported task types."""
    return list(_AGENT_REGISTRY.keys())

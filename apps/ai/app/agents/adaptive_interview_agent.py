"""
Adaptive Interview Agent — Phase 14.

Synthesizes context, response analysis, coverage matrix, and strategy into an advisory recommendation.
Output: AdaptiveRecommendationOutput
"""

import json
import logging
from typing import Any, Dict

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.adaptive import AdaptiveRecommendationOutput

logger = logging.getLogger("interviewos.ai.agents.adaptive")

PROMPT_NAME = "adaptive_interview"


class AdaptiveInterviewAgent(BaseAgent):
    """Generates bounded real-time recommendations for interviewers."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "adaptive_interview"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        current_stage = ctx.extra.get("current_stage", "technical")
        remaining_seconds = ctx.extra.get("remaining_seconds", 900)
        approved_question_plan = ctx.extra.get("approved_question_plan", [])
        uncovered_competencies = ctx.extra.get("uncovered_competencies", [])
        weak_evidence_areas = ctx.extra.get("weak_evidence_areas", [])
        recent_response_analysis = ctx.extra.get("recent_response_analysis", {})
        coding_signals = ctx.extra.get("coding_signals", {})
        system_design_signals = ctx.extra.get("system_design_signals", {})
        resume_claims = ctx.extra.get("resume_claims", [])
        previous_questions_asked = ctx.extra.get("previous_questions_asked", [])

        user_message = f"""Generate the next recommended action for the interviewer.

INTERVIEW STATE:
- Stage: {current_stage}
- Remaining Time: {remaining_seconds} seconds ({remaining_seconds // 60} mins)
- Uncovered High-Priority Competencies: {json.dumps(uncovered_competencies, default=str)}
- Weak Evidence Areas / Gaps: {json.dumps(weak_evidence_areas, default=str)}
- High-Priority Resume Claims: {json.dumps(resume_claims, default=str)}

RECENT SIGNALS:
- Latest Response Analysis: {json.dumps(recent_response_analysis, default=str)}
- Coding Execution State: {json.dumps(coding_signals, default=str)}
- System Design State: {json.dumps(system_design_signals, default=str)}

APPROVED QUESTION PLAN CANDIDATES:
{json.dumps(approved_question_plan, default=str)}

ALREADY ASKED (DO NOT DUPLICATE):
{json.dumps(previous_questions_asked, default=str)}

Recommend the SINGLE highest-value question or follow-up for the interviewer.
Set action to one of: ask_approved_question, generate_follow_up, increase_difficulty, decrease_difficulty, probe_weak_evidence, probe_resume_claim, move_to_next_competency."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.3,
            max_tokens=512,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="adaptive_interview",
        )

        try:
            response = await self.gateway.generate_structured(request, AdaptiveRecommendationOutput)
            result = self._build_success_result(
                ctx=ctx,
                output=response.structured_output,
                response=response,
                confidence=response.structured_output.confidence if response.structured_output else 0.85,
            )
        except AIError as exc:
            result = self._build_error_result(ctx, exc)

        await self._log_result(ctx, result, PROMPT_NAME, prompt_version)
        return result

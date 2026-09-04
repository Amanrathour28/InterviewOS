"""
Coverage Agent — Phase 14.

Evaluates competency coverage against the approved Question Plan.
Output: CompetencyCoverageOutput
"""

import json
import logging
from typing import Any, Dict

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.adaptive import CompetencyCoverageOutput

logger = logging.getLogger("interviewos.ai.agents.coverage")

PROMPT_NAME = "coverage_analysis"


class CoverageAgent(BaseAgent):
    """Evaluates competency coverage matrix and assesses evidence strength."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "coverage_analysis"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        competency = ctx.extra.get("competency", "")
        demonstrated_skills = ctx.extra.get("demonstrated_skills", [])
        questions_asked = ctx.extra.get("questions_asked", 0)
        target_skills = ctx.extra.get("target_skills", [])

        user_message = f"""Assess coverage for competency: {competency}

TARGET SKILLS FOR COMPETENCY:
{json.dumps(target_skills, default=str)}

DEMONSTRATED BY CANDIDATE:
{json.dumps(demonstrated_skills, default=str)}

QUESTIONS ASKED ON THIS COMPETENCY: {questions_asked}

Classify status (not_started, partial, covered, strong, insufficient) and evidence strength (none, weak, moderate, strong)."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=256,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="coverage_analysis",
        )

        try:
            response = await self.gateway.generate_structured(request, CompetencyCoverageOutput)
            result = self._build_success_result(
                ctx=ctx,
                output=response.structured_output,
                response=response,
                confidence=0.90,
            )
        except AIError as exc:
            result = self._build_error_result(ctx, exc)

        await self._log_result(ctx, result, PROMPT_NAME, prompt_version)
        return result

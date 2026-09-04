"""
Difficulty Adaptation Agent — Phase 14.

Calibrates and recommends question difficulty bounded by Question Plan limits.
Output: DifficultyAdaptationOutput
"""

import json
import logging
from typing import Any, Dict

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.adaptive import DifficultyAdaptationOutput

logger = logging.getLogger("interviewos.ai.agents.difficulty")

PROMPT_NAME = "difficulty_adaptation"


class DifficultyAgent(BaseAgent):
    """Calibrates difficulty bounded by interview Question Plan limits."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "difficulty_adaptation"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        current_difficulty = ctx.extra.get("current_difficulty", "medium")
        min_difficulty = ctx.extra.get("min_difficulty", "easy")
        max_difficulty = ctx.extra.get("max_difficulty", "hard")
        evidence_strength = ctx.extra.get("evidence_strength", "moderate")
        recent_performance = ctx.extra.get("recent_performance", {})

        user_message = f"""Calibrate question difficulty for the candidate.

BOUNDS:
- Current Difficulty: {current_difficulty}
- Minimum Allowed: {min_difficulty}
- Maximum Allowed: {max_difficulty}

PERFORMANCE SIGNALS:
- Evidence Strength: {evidence_strength}
- Recent Performance: {json.dumps(recent_performance, default=str)}

Recommend whether to increase, decrease, or maintain difficulty, respecting the min/max bounds."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=256,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="difficulty_adaptation",
        )

        try:
            response = await self.gateway.generate_structured(request, DifficultyAdaptationOutput)
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

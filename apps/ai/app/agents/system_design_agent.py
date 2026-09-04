"""System Design Analysis Agent."""

import json
import logging

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.context.privacy_filter import label_untrusted_content
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.system_design import SystemDesignAnalysis

logger = logging.getLogger("interviewos.ai.agents.system_design")
PROMPT_NAME = "system_design_analysis"


class SystemDesignAgent(BaseAgent):
    """Analyzes whiteboard state + candidate explanation for system design interviews."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "system_design_analysis"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        whiteboard_state = ctx.extra.get("whiteboard_state", {})
        candidate_explanation = ctx.extra.get("candidate_explanation", "")
        problem_statement = ctx.extra.get("problem_statement", "")

        # Use context whiteboard if not in extra
        if not whiteboard_state and ctx.context and ctx.context.whiteboard_state:
            whiteboard_state = ctx.context.whiteboard_state

        # Candidate explanation is UNTRUSTED
        labeled_explanation = (
            label_untrusted_content(candidate_explanation, "CANDIDATE_EXPLANATION")
            if candidate_explanation else ""
        )

        user_message = f"""Analyze the system design whiteboard and candidate's explanation.

PROBLEM STATEMENT:
{problem_statement or 'No problem statement provided.'}

WHITEBOARD STATE (component/connection data):
{json.dumps(whiteboard_state, indent=2, default=str)}

CANDIDATE EXPLANATION:
{labeled_explanation or 'No verbal explanation available.'}

Identify components, analyze scalability and reliability, note bottlenecks,
and suggest follow-up questions. Express confidence appropriately given
the limitations of visual inference from whiteboard data."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.3,
            max_tokens=1024,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="system_design_analysis",
        )

        try:
            response = await self.gateway.generate_structured(request, SystemDesignAnalysis)
            result = self._build_success_result(
                ctx=ctx,
                output=response.structured_output,
                response=response,
                confidence=response.structured_output.confidence if response.structured_output else 0.4,
                evidence=response.structured_output.evidence if response.structured_output else [],
            )
        except AIError as exc:
            result = self._build_error_result(ctx, exc)

        await self._log_result(ctx, result, PROMPT_NAME, prompt_version)
        return result

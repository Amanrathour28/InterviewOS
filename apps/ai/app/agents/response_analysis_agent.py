"""
Response Analysis Agent — Phase 14.

Analyzes candidate response transcripts against expected signals, competencies, and resume claims.
Output: ResponseAnalysisOutput
"""

import json
import logging
from typing import Any, Dict

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.context.privacy_filter import label_untrusted_content
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.adaptive import ResponseAnalysisOutput

logger = logging.getLogger("interviewos.ai.agents.response_analysis")

PROMPT_NAME = "response_analysis"


class ResponseAnalysisAgent(BaseAgent):
    """Evaluates candidate response depth and extracts demonstrated concepts."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "response_analysis"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        current_question = ctx.extra.get("current_question", "")
        candidate_response = ctx.extra.get("candidate_response", "")
        competency = ctx.extra.get("competency", "")
        expected_signal = ctx.extra.get("expected_signal", "")
        claims = ctx.extra.get("claims", [])

        if not candidate_response:
            return self._build_error_result(
                ctx, ValueError("candidate_response is required for response analysis")
            )

        interview_context = ctx.context
        context_dict = interview_context.to_prompt_dict() if interview_context else {}

        labeled_response = label_untrusted_content(candidate_response, "CANDIDATE_RESPONSE")

        user_message = f"""Analyze the candidate's response to the interview question.

INTERVIEW CONTEXT:
{json.dumps(context_dict, indent=2, default=str)}

TARGET COMPETENCY: {competency}
QUESTION ASKED: {current_question}
EXPECTED SIGNAL: {expected_signal}
KNOWN RESUME CLAIMS: {json.dumps(claims, default=str)}

CANDIDATE RESPONSE TRANSCRIPT:
{labeled_response}

Evaluate demonstrated concepts, missing concepts, evidence strength (none, weak, moderate, strong), and completeness score (0.0 - 1.0)."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=512,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="response_analysis",
        )

        try:
            response = await self.gateway.generate_structured(request, ResponseAnalysisOutput)
            result = self._build_success_result(
                ctx=ctx,
                output=response.structured_output,
                response=response,
                confidence=0.88,
                evidence=response.structured_output.demonstrated_concepts if response.structured_output else [],
            )
        except AIError as exc:
            result = self._build_error_result(ctx, exc)

        await self._log_result(ctx, result, PROMPT_NAME, prompt_version)
        return result

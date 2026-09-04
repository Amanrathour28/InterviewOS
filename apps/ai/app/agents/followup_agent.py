"""
Follow-Up Agent.

Given a question + candidate answer, suggests follow-up questions.
Takes into account target skill, difficulty, and remaining time.

Output: FollowUpSuggestion (validated Pydantic schema)

IMPORTANT: This is a suggestion engine, not an autonomous interviewer.
Follow-ups are shown to the interviewer who decides whether to ask them.
"""

import json
import logging

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.question import FollowUpSuggestion

logger = logging.getLogger("interviewos.ai.agents.followup")

PROMPT_NAME = "follow_up"


class FollowUpAgent(BaseAgent):
    """Suggests follow-up questions based on candidate answers."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "follow_up"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        # Required extra params
        question_asked = ctx.extra.get("question_asked", "")
        candidate_answer = ctx.extra.get("candidate_answer", "")
        target_skill = ctx.extra.get("target_skill", "")
        difficulty = ctx.extra.get("difficulty", "medium")
        remaining_seconds = ctx.extra.get("remaining_seconds", 600)

        if not question_asked or not candidate_answer:
            return self._build_error_result(
                ctx, ValueError("question_asked and candidate_answer are required")
            )

        interview_context = ctx.context
        context_dict = interview_context.to_prompt_dict() if interview_context else {}

        from app.context.privacy_filter import label_untrusted_content
        labeled_answer = label_untrusted_content(candidate_answer, "CANDIDATE_ANSWER")

        user_message = f"""Suggest a follow-up question based on the candidate's answer.

INTERVIEW CONTEXT:
{json.dumps(context_dict, indent=2, default=str)}

ORIGINAL QUESTION:
{question_asked}

CANDIDATE ANSWER:
{labeled_answer}

PARAMETERS:
- Target Skill to probe: {target_skill or 'Use judgment from the answer'}
- Desired Difficulty: {difficulty}
- Remaining Interview Time: {remaining_seconds} seconds

Analyze the answer and suggest the SINGLE most valuable follow-up question.
Ground your suggestion in specific aspects of the candidate's answer."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.3,
            max_tokens=512,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="follow_up",
        )

        try:
            response = await self.gateway.generate_structured(request, FollowUpSuggestion)
            result = self._build_success_result(
                ctx=ctx,
                output=response.structured_output,
                response=response,
                confidence=response.structured_output.confidence if response.structured_output else 0.5,
                evidence=response.structured_output.evidence if response.structured_output else [],
            )
        except AIError as exc:
            result = self._build_error_result(ctx, exc)

        await self._log_result(ctx, result, PROMPT_NAME, prompt_version)
        return result

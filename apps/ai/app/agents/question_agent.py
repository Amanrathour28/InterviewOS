"""
Question Generation Agent.

Generates interview questions based on:
  - Job requirements and required skills
  - Interview stage and difficulty
  - Candidate background
  - Previous questions (to avoid repetition)
  - Current topic coverage

Output: GeneratedQuestion (validated Pydantic schema)

This agent produces SUGGESTIONS. The interviewer must explicitly
choose to ask a generated question. Never autonomously asks questions.
"""

import json
import logging
from typing import Optional

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.question import GeneratedQuestion

logger = logging.getLogger("interviewos.ai.agents.question")

PROMPT_NAME = "question_generation"


class QuestionGenerationAgent(BaseAgent):
    """Generates interview questions grounded in job requirements and candidate profile."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "question_generation"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        # Build user message from context
        interview_context = ctx.context
        if not interview_context:
            return self._build_error_result(ctx, ValueError("No interview context provided"))

        context_dict = interview_context.to_prompt_dict()

        # Extract agent-specific parameters from ctx.extra
        difficulty = ctx.extra.get("difficulty", "medium")
        question_type = ctx.extra.get("type", "technical")
        topic_focus = ctx.extra.get("topic_focus", "")
        topics_covered = ctx.extra.get("topics_covered", [])

        user_message = f"""Generate one interview question for the following context.

INTERVIEW CONTEXT:
{json.dumps(context_dict, indent=2, default=str)}

GENERATION REQUIREMENTS:
- Difficulty: {difficulty}
- Question Type: {question_type}
- Topic Focus: {topic_focus or 'Use your judgment based on job requirements'}
- Topics Already Covered: {json.dumps(topics_covered)}
- Do NOT repeat any of the previous questions listed above

Generate a single question that best serves this interview given the context."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.4,  # Slight creativity for variety
            max_tokens=512,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="question_generation",
        )

        try:
            response = await self.gateway.generate_structured(request, GeneratedQuestion)
            result = self._build_success_result(
                ctx=ctx,
                output=response.structured_output,
                response=response,
                confidence=0.85,
            )
        except AIError as exc:
            result = self._build_error_result(ctx, exc)

        await self._log_result(ctx, result, PROMPT_NAME, prompt_version)
        return result

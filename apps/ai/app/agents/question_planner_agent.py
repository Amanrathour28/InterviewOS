"""Question Planning Agent — Generates personalized question plans with difficulty progression."""

import json
import logging

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.context.privacy_filter import filter_candidate, filter_job
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.question_plan import QuestionPlanAnalysis

logger = logging.getLogger("interviewos.ai.agents.question_planner")
PROMPT_NAME = "question_plan"


class QuestionPlanningAgent(BaseAgent):
    """Creates evidence-grounded question plans following difficulty progression."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "question_plan"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        cand_raw = ctx.extra.get("candidate_profile", {})
        job_raw = ctx.extra.get("job_profile", {})
        claims = ctx.extra.get("claims", [])
        gaps = ctx.extra.get("gaps", [])
        blueprint = ctx.extra.get("blueprint", {})

        cand_filtered = filter_candidate(cand_raw)
        job_filtered = filter_job(job_raw)

        user_message = f"""Generate a personalized question plan for this interview.

INTERVIEW BLUEPRINT:
{json.dumps(blueprint, indent=2, default=str)}

JOB SPECIFICATION:
{json.dumps(job_filtered, indent=2, default=str)}

CANDIDATE BACKGROUND:
{json.dumps(cand_filtered, indent=2, default=str)}

CANDIDATE CLAIMS (require probe/verification):
{json.dumps(claims[:8], indent=2, default=str)}

IDENTIFIED GAPS:
{json.dumps(gaps, indent=2, default=str)}

Generate 4-8 ordered questions following difficulty progression:
1. Warm-up (general approach, icebreaker)
2. Fundamental (core concept/language fluency)
3. Practical (production application & trade-offs)
4. Deep Dive (architecture / edge cases / scaling)
5. Verification (specific candidate resume claim probe)

For each question, specify competency, difficulty, expected signal, tested evidence, and follow-up probes."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=2000,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="question_plan",
        )

        try:
            response = await self.gateway.generate_structured(request, QuestionPlanAnalysis)
            result = self._build_success_result(
                ctx=ctx,
                output=response.structured_output,
                response=response,
                confidence=response.structured_output.confidence if response.structured_output else 0.85,
                evidence=response.structured_output.evidence if response.structured_output else [],
            )
        except AIError as exc:
            result = self._build_error_result(ctx, exc)

        await self._log_result(ctx, result, PROMPT_NAME, prompt_version)
        return result

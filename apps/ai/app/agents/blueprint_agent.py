"""Interview Planning Agent — Recommends structured interview blueprints."""

import json
import logging

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.context.privacy_filter import filter_candidate, filter_job
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.blueprint import InterviewBlueprintAnalysis

logger = logging.getLogger("interviewos.ai.agents.blueprint")
PROMPT_NAME = "interview_blueprint"


class InterviewPlanningAgent(BaseAgent):
    """Recommends tailored interview blueprints with rounds, competencies, and durations."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "interview_blueprint"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        cand_raw = ctx.extra.get("candidate_profile", {})
        job_raw = ctx.extra.get("job_profile", {})
        gaps = ctx.extra.get("gaps", [])
        claims = ctx.extra.get("claims", [])
        templates = ctx.extra.get("templates", [])

        cand_filtered = filter_candidate(cand_raw)
        job_filtered = filter_job(job_raw)

        user_message = f"""Generate an interview blueprint recommendation for this candidate and role.

JOB REQUIREMENTS:
{json.dumps(job_filtered, indent=2, default=str)}

CANDIDATE PROFILE:
{json.dumps(cand_filtered, indent=2, default=str)}

IDENTIFIED SKILL GAPS:
{json.dumps(gaps, indent=2, default=str)}

CANDIDATE CLAIMS:
{json.dumps(claims[:8], indent=2, default=str)}

ORGANIZATION TEMPLATES (if any):
{json.dumps(templates[:3], indent=2, default=str)}

Recommend 2-4 appropriate interview rounds with sequence, durations (30-60 min each), key competencies to evaluate, and objectives."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=1500,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="interview_blueprint",
        )

        try:
            response = await self.gateway.generate_structured(request, InterviewBlueprintAnalysis)
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

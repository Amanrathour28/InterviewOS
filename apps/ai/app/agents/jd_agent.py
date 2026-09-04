"""JD Intelligence Agent — Analyzes job descriptions for interview planning."""

import json
import logging

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.context.privacy_filter import filter_job
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.jd import JDAnalysis

logger = logging.getLogger("interviewos.ai.agents.jd")
PROMPT_NAME = "jd_analysis"


class JDAgent(BaseAgent):
    """Analyzes job descriptions to generate interview planning intelligence."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "jd_analysis"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        job_raw = ctx.extra.get("job", {})
        if not job_raw and ctx.context:
            job_raw = ctx.context.job or {}

        job_filtered = filter_job(job_raw)

        user_message = f"""Analyze this job description and extract interview planning intelligence.

JOB DESCRIPTION:
{json.dumps(job_filtered, indent=2, default=str)}

Extract:
1. Required and preferred skills with their relative importance
2. Seniority level indicators
3. Technical domains
4. Interview focus areas
5. Suggested interview rounds structure
6. Question topics for each skill area

Be specific and actionable for interviewers."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,  # Extraction task — low temperature
            max_tokens=1024,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="jd_analysis",
        )

        try:
            response = await self.gateway.generate_structured(request, JDAnalysis)
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

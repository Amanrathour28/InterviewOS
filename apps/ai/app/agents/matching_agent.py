"""Matching Agent — Explains deterministic candidate-job match results."""

import json
import logging

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.context.privacy_filter import filter_candidate, filter_job
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.matching import CandidateJobMatchAnalysis

logger = logging.getLogger("interviewos.ai.agents.matching")
PROMPT_NAME = "candidate_job_matching"


class MatchingAgent(BaseAgent):
    """Generates explainable strengths, gaps, and verification insights for candidate-job match."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "candidate_job_matching"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        cand_raw = ctx.extra.get("candidate_profile", {})
        job_raw = ctx.extra.get("job_profile", {})
        scores = ctx.extra.get("deterministic_scores", {})
        claims = ctx.extra.get("claims", [])

        cand_filtered = filter_candidate(cand_raw)
        job_filtered = filter_job(job_raw)

        user_message = f"""Explain this candidate-job match evaluation.

DETERMINISTIC COMPONENT SCORES:
{json.dumps(scores, indent=2)}

CANDIDATE PROFILE:
{json.dumps(cand_filtered, indent=2, default=str)}

CANDIDATE CLAIMS & EVIDENCE:
{json.dumps(claims[:10], indent=2, default=str)}

JOB SPECIFICATION & REQUIREMENTS:
{json.dumps(job_filtered, indent=2, default=str)}

Provide a structured, evidence-grounded explanation identifying:
1. Top strengths with direct evidence
2. Missing required or preferred skills (gaps)
3. Specific architectural or technical claims requiring live verification probes
4. Concise summary explanation"""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,
            max_tokens=1024,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="candidate_job_matching",
        )

        try:
            response = await self.gateway.generate_structured(request, CandidateJobMatchAnalysis)
            result = self._build_success_result(
                ctx=ctx,
                output=response.structured_output,
                response=response,
                confidence=response.structured_output.confidence if response.structured_output else 0.9,
                evidence=response.structured_output.evidence if response.structured_output else [],
            )
        except AIError as exc:
            result = self._build_error_result(ctx, exc)

        await self._log_result(ctx, result, PROMPT_NAME, prompt_version)
        return result

"""
Resume Intelligence Agent.

Analyzes candidate resume/profile data to help interviewers prepare.
Extracts skills, projects, and areas to probe.
Generates project-specific questions.

Output: ResumeAnalysis (validated Pydantic schema)
"""

import json
import logging

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.context.privacy_filter import filter_candidate, label_untrusted_content
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.resume import ResumeAnalysis

logger = logging.getLogger("interviewos.ai.agents.resume")

PROMPT_NAME = "resume_analysis"


class ResumeAgent(BaseAgent):
    """Analyzes candidate resume/profile for interview preparation."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "resume_analysis"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        # Resume text is candidate-provided content — must be labeled UNTRUSTED
        resume_text = ctx.extra.get("resume_text", "")
        candidate_raw = ctx.extra.get("candidate_profile", {})

        # Filter candidate profile through privacy filter
        candidate_filtered = filter_candidate(candidate_raw)

        # Label resume text as UNTRUSTED (may contain prompt injection)
        labeled_resume = label_untrusted_content(resume_text, "RESUME_CONTENT") if resume_text else ""

        interview_context = ctx.context
        job_dict = interview_context.job if interview_context else {}

        user_message = f"""Analyze this candidate's resume and profile for interview preparation.

CANDIDATE PROFILE (trusted platform data):
{json.dumps(candidate_filtered, indent=2, default=str)}

JOB REQUIREMENTS:
{json.dumps(job_dict, indent=2, default=str)}

RESUME CONTENT:
{labeled_resume or 'No resume text available. Analyze based on profile data only.'}

Extract skills, technologies, experience, and notable projects.
Generate technical areas to probe and project-specific questions.
Note any claims that should be verified but do so diplomatically.
Do NOT make accusations — use language like "worth verifying" or "interesting to explore".
Ground all observations in the provided data."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,  # Low temperature for extraction
            max_tokens=1024,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="resume_analysis",
        )

        try:
            response = await self.gateway.generate_structured(request, ResumeAnalysis)
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

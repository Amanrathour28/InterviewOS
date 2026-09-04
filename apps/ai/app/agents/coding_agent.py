"""
Coding Analysis Agent.

Analyzes coding artifacts (code, execution results, submission history).
Provides reasoning and explanations — NEVER overrides sandbox results.

INVARIANT: If sandbox says 8/10 tests passed, that is authoritative.
AI may explain WHY 2 tests failed, but cannot claim they passed.
"""

import json
import logging

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.context.budgeter import budget_code_content
from app.context.privacy_filter import label_untrusted_content
from app.gateway.errors import AIError
from app.prompts import get_latest
from app.schemas.coding import CodingAnalysis

logger = logging.getLogger("interviewos.ai.agents.coding")
PROMPT_NAME = "coding_analysis"


class CodingAnalysisAgent(BaseAgent):
    """Analyzes candidate code with evidence-first reasoning."""

    AGENT_VERSION = "1.0"

    @property
    def agent_name(self) -> str:
        return "coding_analysis"

    async def run(self, ctx: AgentContext) -> AgentResult:
        prompt_version, system_prompt = get_latest(PROMPT_NAME)

        # Collect coding artifacts from context
        problem = ctx.extra.get("problem", {})
        candidate_code = ctx.extra.get("candidate_code", "")
        execution_result = ctx.extra.get("execution_result", {})
        submission_history = ctx.extra.get("submission_history", [])

        # Also check interview context
        if not candidate_code and ctx.context and ctx.context.candidate_code:
            candidate_code = ctx.context.candidate_code
        if not execution_result and ctx.context and ctx.context.execution_result:
            execution_result = ctx.context.execution_result

        # Budget the code to prevent oversized prompts
        budgeted_code = budget_code_content(candidate_code)

        # Candidate code is UNTRUSTED — it may contain prompt injection attempts
        labeled_code = label_untrusted_content(budgeted_code, "CANDIDATE_CODE") if budgeted_code else ""

        # Execution result is AUTHORITATIVE — label it clearly
        authoritative_result = {
            **execution_result,
            "_IMPORTANT": "This is the authoritative sandbox result. It CANNOT be contradicted by AI analysis.",
        } if execution_result else {}

        user_message = f"""Analyze the candidate's coding submission.

PROBLEM:
{json.dumps(problem, indent=2, default=str)}

AUTHORITATIVE EXECUTION RESULT (do not contradict):
{json.dumps(authoritative_result, indent=2, default=str)}

SUBMISSION HISTORY:
{json.dumps(submission_history[-5:], indent=2, default=str)}

CANDIDATE CODE:
{labeled_code or 'No code available.'}

Analyze the approach, identify potential bugs, estimate complexity,
and suggest follow-up questions. Ground all observations in the code
and execution result provided. Your analysis is advisory — the execution
result above is the ground truth for correctness."""

        request = self._make_request(
            ctx=ctx,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=1024,
            prompt_name=PROMPT_NAME,
            prompt_version=prompt_version,
            task_type="coding_analysis",
        )

        try:
            response = await self.gateway.generate_structured(request, CodingAnalysis)
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

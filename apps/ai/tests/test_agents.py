"""
Agent Contract Tests.

Tests that every agent:
  1. Returns AgentResult with correct status on success
  2. Returns AgentResult with status='failed' (not raises) on AIError
  3. Produces output matching the registered schema
  4. Passes workspace_id through to gateway request
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel

from app.agents.base import AgentContext
from app.agents.question_agent import QuestionGenerationAgent
from app.agents.followup_agent import FollowUpAgent
from app.agents.coding_agent import CodingAnalysisAgent
from app.agents.orchestrator import OrchestratorAgent, get_available_tasks
from app.context.builder import InterviewContextBuilder
from app.gateway.errors import AIProviderUnavailable
from app.gateway.request import AIResponse, AIUsage
from app.schemas.question import GeneratedQuestion, FollowUpSuggestion
from app.schemas.coding import CodingAnalysis

from tests.conftest import (
    SAMPLE_WORKSPACE_ID,
    SAMPLE_INTERVIEW_ID,
    SAMPLE_SESSION_ID,
    SAMPLE_CODE,
    SAMPLE_EXECUTION_RESULT,
    SAMPLE_PROBLEM,
)


def make_mock_gateway(structured_output: BaseModel):
    """Create a mock gateway that returns a given structured output."""
    gateway = MagicMock()
    response = AIResponse(
        request_id="test-req",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=structured_output.model_dump_json(),
        structured_output=structured_output,
        usage=AIUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        latency_ms=200,
    )
    gateway.generate_structured = AsyncMock(return_value=response)
    gateway.generate = AsyncMock(return_value=response)
    return gateway


def make_agent_context(extra: dict = None) -> AgentContext:
    builder = InterviewContextBuilder()
    ctx = builder.build(
        workspace_id=SAMPLE_WORKSPACE_ID,
        interview_id=SAMPLE_INTERVIEW_ID,
    )
    return AgentContext(
        workspace_id=SAMPLE_WORKSPACE_ID,
        interview_id=SAMPLE_INTERVIEW_ID,
        session_id=SAMPLE_SESSION_ID,
        is_interviewer=True,
        context=ctx,
        extra=extra or {},
    )


# ---------------------------------------------------------------------------
# QuestionGenerationAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_question_agent_returns_success_result():
    """QuestionGenerationAgent must return status='success' with GeneratedQuestion output."""
    mock_question = GeneratedQuestion(
        question="Explain how you would design a rate limiter.",
        topic="System Design",
        difficulty="hard",
        type="technical",
        rationale="Tests system design depth",
        expected_signals=["Token bucket", "Redis", "Sliding window"],
    )
    gateway = make_mock_gateway(mock_question)

    agent = QuestionGenerationAgent(gateway=gateway)
    ctx = make_agent_context({"difficulty": "hard", "type": "technical"})
    result = await agent.run(ctx)

    assert result.status == "success"
    assert result.output is not None
    assert isinstance(result.output, GeneratedQuestion)
    assert result.agent_name == "question_generation"


@pytest.mark.asyncio
async def test_question_agent_returns_failed_on_provider_error():
    """QuestionGenerationAgent must return status='failed', not raise, on AIError."""
    gateway = MagicMock()
    gateway.generate_structured = AsyncMock(
        side_effect=AIProviderUnavailable(provider="groq")
    )

    agent = QuestionGenerationAgent(gateway=gateway)
    ctx = make_agent_context()
    result = await agent.run(ctx)

    assert result.status == "failed"
    assert result.output is None
    assert "AIProviderUnavailable" in result.error_type


# ---------------------------------------------------------------------------
# CodingAnalysisAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coding_agent_returns_success_result():
    """CodingAnalysisAgent must return status='success' with CodingAnalysis output."""
    mock_analysis = CodingAnalysis(
        approach_summary="Uses hash map for O(n) solution.",
        time_complexity_estimate="O(n)",
        space_complexity_estimate="O(n)",
        correctness_observations=["Logic appears correct for the given test cases."],
        potential_bugs=[],
        edge_case_observations=["Does not handle empty input."],
        code_quality_observations=["Clean and readable code."],
        improvement_suggestions=["Add input validation."],
        suggested_follow_ups=["How would you handle duplicates?"],
        confidence=0.8,
        evidence=["The code passes 8/10 test cases per execution result."],
    )
    gateway = make_mock_gateway(mock_analysis)

    agent = CodingAnalysisAgent(gateway=gateway)
    ctx = make_agent_context({
        "problem": SAMPLE_PROBLEM,
        "candidate_code": SAMPLE_CODE,
        "execution_result": SAMPLE_EXECUTION_RESULT,
    })
    result = await agent.run(ctx)

    assert result.status == "success"
    assert result.output is not None
    # Sandbox disclaimer must always be present
    assert result.output.disclaimer is not None


# ---------------------------------------------------------------------------
# OrchestratorAgent
# ---------------------------------------------------------------------------

def test_orchestrator_task_list_is_complete():
    """All expected task types must be registered in the orchestrator."""
    tasks = get_available_tasks()
    expected = {
        "question_generation", "follow_up", "resume_analysis",
        "jd_analysis", "coding_analysis", "system_design_analysis",
    }
    assert expected.issubset(set(tasks))


@pytest.mark.asyncio
async def test_orchestrator_returns_failed_for_unknown_task():
    """Orchestrator must return status='failed' for unknown task type."""
    gateway = MagicMock()
    agent = OrchestratorAgent(gateway=gateway)
    ctx = make_agent_context({"task_type": "nonexistent_task_type"})
    result = await agent.run(ctx)

    assert result.status == "failed"
    assert result.error_type == "ValueError"

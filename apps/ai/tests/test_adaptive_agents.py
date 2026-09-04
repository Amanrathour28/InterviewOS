import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.adaptive_interview_agent import AdaptiveInterviewAgent
from app.agents.base import AgentContext
from app.agents.coverage_agent import CoverageAgent
from app.agents.difficulty_agent import DifficultyAgent
from app.agents.response_analysis_agent import ResponseAnalysisAgent
from app.gateway.request import AIResponse, AIUsage
from app.orchestrator.adaptive_graph import build_adaptive_graph
from app.schemas.adaptive import (
    AdaptiveRecommendationOutput,
    CompetencyCoverageOutput,
    DifficultyAdaptationOutput,
    ResponseAnalysisOutput,
)


@pytest.mark.asyncio
async def test_response_analysis_agent_structured_output():
    mock_output = ResponseAnalysisOutput(
        completeness_score=0.85,
        demonstrated_concepts=["Redis caching", "Latency reduction", "Hot key handling"],
        missing_concepts=["Cache invalidation", "TTL expiration"],
        evidence_strength="moderate",
        suggested_probe_angles=["Ask how cache consistency is maintained"],
        summary="Candidate effectively described Redis deployment for hot sessions.",
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-resp-an",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=150, output_tokens=80, total_tokens=230),
        latency_ms=120,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = ResponseAnalysisAgent(gateway=gateway)
    ctx = AgentContext(
        workspace_id="ws-test",
        interview_id="itw-test",
        extra={
            "current_question": "How did you design your caching layer?",
            "candidate_response": "We implemented Redis for caching hot session keys, reducing database queries by 70%, but didn't have TTLs at first.",
            "competency": "Caching & Databases",
            "expected_signal": "Cache invalidation and eviction policies",
        },
    )

    result = await agent.run(ctx)
    assert result.status == "success"
    assert result.output is not None
    assert result.output.completeness_score == 0.85
    assert len(result.output.demonstrated_concepts) == 3


@pytest.mark.asyncio
async def test_difficulty_agent_bounds():
    mock_output = DifficultyAdaptationOutput(
        current_difficulty="medium",
        recommended_difficulty="hard",
        adjustment_direction="increase",
        rationale="Candidate demonstrated deep mastery of caching and requested more complex distributed problems.",
        confidence=0.9,
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-diff",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        latency_ms=90,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = DifficultyAgent(gateway=gateway)
    ctx = AgentContext(
        workspace_id="ws-test",
        interview_id="itw-test",
        extra={
            "current_difficulty": "medium",
            "min_difficulty": "easy",
            "max_difficulty": "hard",
            "evidence_strength": "strong",
            "recent_performance": {"completeness_score": 0.95},
        },
    )

    result = await agent.run(ctx)
    assert result.status == "success"
    assert result.output is not None
    assert result.output.recommended_difficulty == "hard"


@pytest.mark.asyncio
async def test_coverage_agent():
    mock_output = CompetencyCoverageOutput(
        competency="Distributed Systems",
        status="covered",
        evidence_strength="strong",
        demonstrated_skills=["consensus", "partitioning", "replication"],
        missing_skills=[],
        reasoning="Candidate answered distributed system failure scenarios thoroughly.",
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-cov",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        latency_ms=80,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = CoverageAgent(gateway=gateway)
    ctx = AgentContext(
        workspace_id="ws-test",
        interview_id="itw-test",
        extra={
            "competency": "Distributed Systems",
            "demonstrated_skills": ["consensus", "partitioning"],
            "questions_asked": 2,
            "target_skills": ["consensus", "partitioning", "replication", "leader election"],
        },
    )

    result = await agent.run(ctx)
    assert result.status == "success"
    assert result.output is not None
    assert result.output.status == "covered"


@pytest.mark.asyncio
async def test_adaptive_graph_workflow():
    resp_an_out = ResponseAnalysisOutput(
        completeness_score=0.8,
        demonstrated_concepts=["B-Tree indexing", "Range query performance"],
        missing_concepts=["Write amplification", "Index maintenance cost"],
        evidence_strength="moderate",
        suggested_probe_angles=["Ask about indexing overhead on write-heavy workloads"],
    )
    cov_out = CompetencyCoverageOutput(
        competency="Databases",
        status="partial",
        evidence_strength="moderate",
    )
    diff_out = DifficultyAdaptationOutput(
        current_difficulty="medium",
        recommended_difficulty="medium",
        adjustment_direction="maintain",
    )
    rec_out = AdaptiveRecommendationOutput(
        action="generate_follow_up",
        recommended_question="How does adding multiple B-Tree indexes impact your write throughput and storage overhead?",
        competency="Databases",
        difficulty="medium",
        reason="Candidate knows query indexing well; probe write amplification trade-offs.",
        evidence_target="Write amplification and index maintenance overhead",
        time_cost_estimate_seconds=180,
        confidence=0.88,
        requires_approval=True,
    )

    def side_effect(request, schema):
        if schema == ResponseAnalysisOutput:
            obj = resp_an_out
        elif schema == CompetencyCoverageOutput:
            obj = cov_out
        elif schema == DifficultyAdaptationOutput:
            obj = diff_out
        else:
            obj = rec_out

        return AIResponse(
            request_id="req-test-adapt",
            provider="groq",
            model="llama-3.3-70b-versatile",
            content=obj.model_dump_json(),
            structured_output=obj,
            usage=AIUsage(input_tokens=150, output_tokens=70, total_tokens=220),
            latency_ms=100,
        )

    gateway = MagicMock()
    gateway.generate_structured = AsyncMock(side_effect=side_effect)

    orchestrator = build_adaptive_graph(gateway=gateway)
    initial_state = {
        "workspace_id": "ws-test",
        "interview_id": "itw-test",
        "session_id": "sess-test",
        "user_id": "usr-test",
        "current_stage": "technical",
        "remaining_seconds": 600,
        "current_question": "Explain your database indexing strategy.",
        "candidate_response": "We added B-Tree indexes on tenant_id and created_at columns for quick range queries.",
        "competency": "Databases",
        "expected_signal": "Index types and query optimization",
        "approved_question_plan": [
            {"title": "Database Indexing", "competency": "Databases", "difficulty": "medium"}
        ],
        "resume_claims": [{"claim": "Optimized database performance by 40%"}],
        "coding_signals": {},
        "system_design_signals": {},
        "previous_questions_asked": [],
        "response_analysis": None,
        "difficulty_adaptation": None,
        "coverage_state": None,
        "recommendation": None,
        "error": None,
    }

    final_state = await orchestrator.ainvoke(initial_state)
    assert final_state["recommendation"] is not None
    rec = final_state["recommendation"]
    assert "recommended_question" in rec
    assert rec["requires_approval"] is True


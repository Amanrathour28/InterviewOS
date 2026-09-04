import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.base import AgentContext
from app.agents.matching_agent import MatchingAgent
from app.agents.blueprint_agent import InterviewPlanningAgent
from app.agents.question_planner_agent import QuestionPlanningAgent
from app.context.builder import InterviewContextBuilder
from app.gateway.request import AIResponse, AIUsage
from app.schemas.matching import CandidateJobMatchAnalysis, MatchStrength, MatchGap, MatchVerificationArea
from app.schemas.blueprint import InterviewBlueprintAnalysis, BlueprintRoundRecommendation
from app.schemas.question_plan import QuestionPlanAnalysis, QuestionPlanItemRecommendation
from app.orchestrator.planning_graph import run_planning_workflow

from tests.conftest import (
    SAMPLE_WORKSPACE_ID,
    SAMPLE_INTERVIEW_ID,
)

def make_agent_context(extra: dict = None) -> AgentContext:
    builder = InterviewContextBuilder()
    ctx = builder.build(
        workspace_id=SAMPLE_WORKSPACE_ID,
        interview_id=SAMPLE_INTERVIEW_ID,
    )
    return AgentContext(
        context=ctx,
        workspace_id=SAMPLE_WORKSPACE_ID,
        interview_id=SAMPLE_INTERVIEW_ID,
        extra=extra or {},
    )

@pytest.mark.asyncio
async def test_matching_agent_structured_output():
    mock_output = CandidateJobMatchAnalysis(
        summary_explanation="Strong match with comprehensive required skills coverage and relevant experience.",
        strengths=[
            MatchStrength(skill="Python", evidence="6 years backend experience building microservices"),
            MatchStrength(skill="FastAPI", evidence="Production API development"),
        ],
        gaps=[
            MatchGap(skill="Kubernetes", reason="No direct production cluster orchestration cited"),
        ],
        verification_areas=[
            MatchVerificationArea(topic="Kafka Partitioning", reason="Verify high-throughput claims"),
        ],
        confidence=0.92,
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-match",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=200, output_tokens=100, total_tokens=300),
        latency_ms=150,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = MatchingAgent(gateway=gateway)
    ctx = make_agent_context({
        "candidate_profile": {"skills": ["Python", "FastAPI"], "years_experience": 6},
        "job_profile": {"required_skills": ["Python", "FastAPI"]},
        "deterministic_scores": {"overall_score": 90.0},
    })

    result = await agent.run(ctx)
    assert result.status == "success"
    assert result.output.summary_explanation is not None
    assert len(result.output.strengths) == 2

@pytest.mark.asyncio
async def test_blueprint_agent_structured_output():
    mock_output = InterviewBlueprintAnalysis(
        title="Senior Backend Engineering Blueprint",
        target_seniority="senior",
        total_duration_minutes=120,
        rounds=[
            BlueprintRoundRecommendation(
                name="System Architecture & Concurrency",
                round_type="system_design",
                sequence=1,
                duration_minutes=60,
                difficulty="senior",
                scoring_weight=1.5,
                objectives=["Assess distributed caching", "Evaluate fault tolerance"],
                competencies=["Distributed Systems", "PostgreSQL", "Kafka"],
            ),
            BlueprintRoundRecommendation(
                name="Live Hands-on Coding",
                round_type="coding",
                sequence=2,
                duration_minutes=60,
                difficulty="mid",
                scoring_weight=1.0,
                objectives=["Assess data structure selection and clean code"],
                competencies=["Python", "Algorithms"],
            ),
        ],
        confidence=0.88,
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-bp",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=300, output_tokens=200, total_tokens=500),
        latency_ms=250,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = InterviewPlanningAgent(gateway=gateway)
    ctx = make_agent_context({
        "candidate_claims": ["Designed Kafka pipeline"],
        "job_requirements": ["High-throughput backend"],
        "custom_requirements": ["Include system design and coding"],
    })

    result = await agent.run(ctx)
    assert result.status == "success"
    assert len(result.output.rounds) == 2
    assert result.output.rounds[0].round_type == "system_design"

@pytest.mark.asyncio
async def test_question_planner_agent_structured_output():
    mock_output = QuestionPlanAnalysis(
        title="Personalized Senior Question Plan",
        target_competencies=["Kafka", "Distributed Systems"],
        questions=[
            QuestionPlanItemRecommendation(
                sequence=1,
                title="Kafka Partitioning Strategy",
                prompt="How did you implement message partitioning and deduplication in your Kafka pipeline?",
                competency="Kafka",
                difficulty="hard",
                progression_stage="deep_dive",
                expected_signal="Partition keys, idempotent producers, consumer rebalance handling",
                candidate_evidence_tested="Designed multi-region Kafka data pipeline",
            )
        ],
        confidence=0.9,
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-qp",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=250, output_tokens=150, total_tokens=400),
        latency_ms=180,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = QuestionPlanningAgent(gateway=gateway)
    ctx = make_agent_context({
        "target_difficulty": "hard",
        "focus_areas": ["Kafka", "Distributed Systems"],
    })

    result = await agent.run(ctx)
    assert result.status == "success"
    assert len(result.output.questions) == 1
    assert result.output.questions[0].competency == "Kafka"

@pytest.mark.asyncio
async def test_planning_graph_workflow():
    gateway = MagicMock()
    bp_output = InterviewBlueprintAnalysis(
        title="Graph Planned Blueprint",
        target_seniority="mid",
        total_duration_minutes=60,
        rounds=[
            BlueprintRoundRecommendation(
                name="Coding Assessment",
                round_type="coding",
                sequence=1,
                duration_minutes=60,
                difficulty="mid",
                scoring_weight=1.0,
                objectives=["Assess problem solving"],
                competencies=["Python"],
            )
        ],
        confidence=0.85,
    )
    qp_output = QuestionPlanAnalysis(
        title="Graph Planned Questions",
        target_competencies=["Python"],
        questions=[
            QuestionPlanItemRecommendation(
                sequence=1,
                title="Python Concurrency Models",
                prompt="Explain Python GIL and concurrency models in production services.",
                competency="Python",
                difficulty="medium",
                progression_stage="practical",
                expected_signal="GIL lock contention, multiprocessing vs asyncio",
            )
        ],
        confidence=0.85,
    )

    def side_effect(request, schema):
        resp_obj = bp_output if schema == InterviewBlueprintAnalysis else qp_output
        return AIResponse(
            request_id="req-graph",
            provider="groq",
            model="llama-3.3-70b-versatile",
            content=resp_obj.model_dump_json(),
            structured_output=resp_obj,
            usage=AIUsage(input_tokens=100, output_tokens=50, total_tokens=150),
            latency_ms=100,
        )

    gateway.generate_structured = AsyncMock(side_effect=side_effect)

    final_state = await run_planning_workflow(
        workspace_id=SAMPLE_WORKSPACE_ID,
        candidate_id="cand-123",
        job_id="job-123",
        interview_id=SAMPLE_INTERVIEW_ID,
        gateway=gateway,
    )

    assert final_state["status"] == "completed"
    assert final_state["blueprint"] is not None
    assert final_state["question_plan"] is not None

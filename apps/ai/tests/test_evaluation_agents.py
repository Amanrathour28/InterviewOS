"""
Unit and orchestration tests for Phase 15 AI Evaluation Agents & Multi-Agent Graph.
Tests:
- EvidenceAnalysisAgent structured parsing & synthesis
- CodingEvaluationAgent deterministic execution alignment
- ContradictionDetectionAgent resume vs interview verification
- EvaluationSynthesisAgent executive summary and matrix assembly
- Evaluation Multi-Agent Graph execution
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.base import AgentContext
from app.agents.evaluation_agents import (
    EvidenceAnalysisAgent,
    TechnicalEvaluationAgent,
    CodingEvaluationAgent,
    ContradictionDetectionAgent,
    EvaluationSynthesisAgent,
)
from app.gateway.request import AIResponse, AIUsage
from app.orchestrator.evaluation_graph import build_evaluation_graph
from app.schemas.evaluation import (
    EvidenceAnalysisOutput,
    CompetencyEvaluationOutput,
    CodingEvaluationOutput,
    ContradictionDetectionOutput,
    ContradictionItem,
    EvaluationSynthesisOutput,
)


@pytest.mark.asyncio
async def test_evidence_analysis_agent_structured_output():
    mock_output = EvidenceAnalysisOutput(
        key_themes=["High throughput distributed streaming", "Docker microservices architecture"],
        technical_signals=["Demonstrated Kafka partitioning knowledge", "Understands consumer lag"],
        strengths=["Strong grasp of distributed stream processing"],
        weaknesses=["Did not elaborate on schema evolution / Avro registry"],
        confidence=0.92,
        unsupported_claims=["Claimed to scale Kafka to 10M QPS with single broker"],
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-eval-ev",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=180, output_tokens=95, total_tokens=275),
        latency_ms=130,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = EvidenceAnalysisAgent(gateway=gateway)
    ctx = AgentContext(
        workspace_id="ws-123",
        interview_id="itw-123",
        extra={
            "job_title": "Staff Backend Engineer",
            "candidate_name": "Ada Lovelace",
            "normalized_evidence": [
                {"id": "ev-1", "evidence_type": "transcript", "content": "I built Kafka ingestion pipelines for streaming."},
            ],
        },
    )
    result = await agent.execute(ctx)
    assert result.confidence == 0.92
    assert "High throughput distributed streaming" in result.key_themes
    assert len(result.unsupported_claims) == 1


@pytest.mark.asyncio
async def test_coding_evaluation_agent():
    mock_output = CodingEvaluationOutput(
        competency_name="Data Structures & Algorithms",
        rubric_level=4,
        confidence=0.95,
        strengths=["Optimal O(N) time and O(1) space complexity", "Clean modular variable naming"],
        weaknesses=["Initially missed empty array edge case before hint"],
        citations=["ev-docker-1"],
        correctness_score=90.0,
        code_quality_score=85.0,
        algorithmic_efficiency_score=95.0,
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-eval-code",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=220, output_tokens=110, total_tokens=330),
        latency_ms=145,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = CodingEvaluationAgent(gateway=gateway)
    ctx = AgentContext(
        workspace_id="ws-123",
        interview_id="itw-123",
        extra={
            "coding_evidence": [
                {"id": "ev-docker-1", "passed_tests": 10, "total_tests": 10, "execution_time_ms": 42},
            ],
            "rubrics": [],
        },
    )
    result = await agent.execute(ctx)
    assert result.rubric_level == 4
    assert result.correctness_score == 90.0
    assert "ev-docker-1" in result.citations


@pytest.mark.asyncio
async def test_contradiction_detection_agent():
    mock_output = ContradictionDetectionOutput(
        contradictions=[
            ContradictionItem(
                category="resume_vs_performance",
                severity="medium",
                claim="Lead architect of multi-region Kubernetes cluster",
                observed_evidence="Struggled to explain basic Service / Ingress differences",
                explanation="Candidate resume claims Kubernetes architecture ownership, but interview demonstrated beginner knowledge.",
                evidence_ids=["ev-resume-1", "ev-trans-4"],
            )
        ],
        unverified_claims=["5 years Rust production experience"],
        integrity_score=75.0,
    )

    gateway = MagicMock()
    response = AIResponse(
        request_id="req-eval-contra",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content=mock_output.model_dump_json(),
        structured_output=mock_output,
        usage=AIUsage(input_tokens=200, output_tokens=90, total_tokens=290),
        latency_ms=125,
    )
    gateway.generate_structured = AsyncMock(return_value=response)

    agent = ContradictionDetectionAgent(gateway=gateway)
    ctx = AgentContext(
        workspace_id="ws-123",
        interview_id="itw-123",
        extra={
            "resume_claims": [{"id": "ev-resume-1", "text": "Lead architect of multi-region Kubernetes cluster"}],
            "normalized_evidence": [{"id": "ev-trans-4", "text": "I mostly just used kubectl apply for pods"}],
        },
    )
    result = await agent.execute(ctx)
    assert len(result.contradictions) == 1
    assert result.integrity_score == 75.0
    assert result.contradictions[0].severity == "medium"


@pytest.mark.asyncio
async def test_evaluation_multi_agent_graph():
    gateway = MagicMock()

    ev_out = EvidenceAnalysisOutput(
        key_themes=["Distributed Systems"],
        technical_signals=["Understands Paxos"],
        strengths=["Strong consensus grasp"],
        weaknesses=[],
        confidence=0.9,
    )
    tech_out = CompetencyEvaluationOutput(
        competency_name="System Architecture",
        rubric_level=5,
        confidence=0.95,
        strengths=["Excellent Paxos vs Raft trade-off analysis"],
        weaknesses=[],
        citations=["ev-1"],
    )
    code_out = CodingEvaluationOutput(
        competency_name="Coding & Algorithms",
        rubric_level=4,
        confidence=0.9,
        strengths=["Clean Python solution"],
        weaknesses=[],
        citations=["ev-2"],
        correctness_score=100.0,
        code_quality_score=85.0,
        algorithmic_efficiency_score=90.0,
    )
    contra_out = ContradictionDetectionOutput(
        contradictions=[],
        unverified_claims=[],
        integrity_score=100.0,
    )
    synth_out = EvaluationSynthesisOutput(
        executive_summary="Candidate demonstrated exceptional technical mastery in distributed systems.",
        overall_recommendation="STRONG_HIRE",
        hiring_confidence=0.96,
        key_strengths=["Deep distributed consensus understanding", "Clean algorithmic code"],
        key_weaknesses=["Could improve test coverage"],
        recommended_level="Senior Software Engineer II",
        risk_factors=[],
    )

    async def mock_gen_struct(request, schema=None, **kwargs):
        target_schema = schema or getattr(request, "response_schema", None)
        if target_schema == EvidenceAnalysisOutput:
            return AIResponse(request_id="1", provider="groq", model="model", content=ev_out.model_dump_json(), structured_output=ev_out, usage=AIUsage(input_tokens=1, output_tokens=1, total_tokens=2), latency_ms=10)
        elif target_schema == CodingEvaluationOutput:
            return AIResponse(request_id="2", provider="groq", model="model", content=code_out.model_dump_json(), structured_output=code_out, usage=AIUsage(input_tokens=1, output_tokens=1, total_tokens=2), latency_ms=10)
        elif target_schema == ContradictionDetectionOutput:
            return AIResponse(request_id="3", provider="groq", model="model", content=contra_out.model_dump_json(), structured_output=contra_out, usage=AIUsage(input_tokens=1, output_tokens=1, total_tokens=2), latency_ms=10)
        elif target_schema == EvaluationSynthesisOutput:
            return AIResponse(request_id="4", provider="groq", model="model", content=synth_out.model_dump_json(), structured_output=synth_out, usage=AIUsage(input_tokens=1, output_tokens=1, total_tokens=2), latency_ms=10)
        else:
            return AIResponse(request_id="5", provider="groq", model="model", content=tech_out.model_dump_json(), structured_output=tech_out, usage=AIUsage(input_tokens=1, output_tokens=1, total_tokens=2), latency_ms=10)

    gateway.generate_structured = AsyncMock(side_effect=mock_gen_struct)

    graph = build_evaluation_graph(gateway=gateway)
    initial_state = {
        "workspace_id": "ws-100",
        "interview_id": "itw-100",
        "candidate_name": "Katherine Johnson",
        "job_title": "Orbital Mechanics Lead",
        "normalized_evidence": [{"id": "ev-1", "content": "Trajectory calculations"}],
        "coding_evidence": [{"id": "ev-2", "passed_tests": 10, "total_tests": 10}],
        "resume_claims": [],
        "competencies": [{"name": "System Architecture", "weight": 1.0}],
    }

    final_state = await graph.ainvoke(initial_state)
    assert final_state["evidence_analysis"] is not None
    assert final_state["contradiction_analysis"] is not None
    assert final_state["synthesis"] is not None
    assert final_state["synthesis"]["overall_recommendation"] == "STRONG_HIRE"
    assert len(final_state["competency_scores"]) >= 1

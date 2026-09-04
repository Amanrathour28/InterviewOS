"""
Test fixtures for InterviewOS AI service tests.

Provides realistic test data without requiring a live database or AI provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.context.builder import InterviewContext, InterviewContextBuilder
from app.gateway.request import AIRequest, AIResponse, AIUsage, AIMessage
from app.agents.base import AgentContext


# ---------------------------------------------------------------------------
# Sample Data Fixtures
# ---------------------------------------------------------------------------

SAMPLE_WORKSPACE_ID = "workspace-test-001"
SAMPLE_INTERVIEW_ID = "interview-test-001"
SAMPLE_SESSION_ID = "session-test-001"
SAMPLE_USER_ID = "user-interviewer-001"


SAMPLE_CANDIDATE = {
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice@example.com",
    "headline": "Senior Software Engineer",
    "current_company": "TechCorp",
    "current_title": "Staff Engineer",
    "experience_years": 6.0,
    "skills": ["Python", "Go", "Kubernetes", "PostgreSQL"],
    # These should be filtered out by privacy filter:
    "password": "should_be_removed",
    "secret_key": "should_be_removed",
}

SAMPLE_JOB = {
    "title": "Senior Backend Engineer",
    "department": "Engineering",
    "description": "Build scalable Python/Go microservices",
    "required_skills": ["Python", "PostgreSQL", "System Design"],
    "preferred_skills": ["Go", "Kubernetes"],
    "experience_min": 4,
    "experience_max": 8,
    # These should be filtered:
    "salary_min": 120000,
    "salary_max": 180000,
}

SAMPLE_EVENTS = [
    {
        "event_type": "SESSION_STARTED",
        "sequence": 1,
        "timestamp": "2025-01-01T10:00:00Z",
        "actor_role": "interviewer",
        "payload": {"stage": "introduction"},
    },
    {
        "event_type": "STAGE_CHANGED",
        "sequence": 2,
        "timestamp": "2025-01-01T10:05:00Z",
        "actor_role": "interviewer",
        "payload": {"new_stage": "coding"},
    },
    {
        "event_type": "PRIVATE_INTERVIEWER_NOTE",  # Should be filtered out
        "sequence": 3,
        "timestamp": "2025-01-01T10:06:00Z",
        "actor_role": "interviewer",
        "payload": {"note": "candidate seems nervous"},
    },
    {
        "event_type": "CODE_EXECUTION_COMPLETED",
        "sequence": 4,
        "timestamp": "2025-01-01T10:15:00Z",
        "actor_role": "system",
        "payload": {
            "tests_passed": 8,
            "tests_total": 10,
            "status": "completed",
        },
    },
]

SAMPLE_PROBLEM = {
    "title": "Two Sum",
    "difficulty": "medium",
    "category": "arrays",
    "problem_statement": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
}

SAMPLE_CODE = """def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
"""

SAMPLE_EXECUTION_RESULT = {
    "status": "completed",
    "tests_passed": 8,
    "tests_total": 10,
    "runtime_ms": 45,
    "memory_mb": 12.5,
}


# ---------------------------------------------------------------------------
# Context Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_interview_context() -> InterviewContext:
    builder = InterviewContextBuilder()
    return builder.build(
        workspace_id=SAMPLE_WORKSPACE_ID,
        interview_id=SAMPLE_INTERVIEW_ID,
        session_id=SAMPLE_SESSION_ID,
        user_id=SAMPLE_USER_ID,
        current_stage="coding",
        elapsed_seconds=900,
        raw_candidate=SAMPLE_CANDIDATE,
        raw_job=SAMPLE_JOB,
        raw_events=SAMPLE_EVENTS,
        current_problem=SAMPLE_PROBLEM,
        candidate_code=SAMPLE_CODE,
        execution_result=SAMPLE_EXECUTION_RESULT,
    )


@pytest.fixture
def sample_agent_context(sample_interview_context) -> AgentContext:
    return AgentContext(
        workspace_id=SAMPLE_WORKSPACE_ID,
        interview_id=SAMPLE_INTERVIEW_ID,
        session_id=SAMPLE_SESSION_ID,
        user_id=SAMPLE_USER_ID,
        current_stage="coding",
        is_interviewer=True,
        context=sample_interview_context,
        extra={},
    )


# ---------------------------------------------------------------------------
# Mock Provider Fixture
# ---------------------------------------------------------------------------

def make_mock_response(content: str, provider: str = "groq") -> AIResponse:
    return AIResponse(
        request_id="test-req-001",
        provider=provider,
        model="llama-3.3-70b-versatile",
        content=content,
        usage=AIUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        latency_ms=250,
    )


@pytest.fixture
def mock_gateway():
    """Gateway that returns a predictable structured response."""
    gateway = MagicMock()
    gateway.generate = AsyncMock()
    gateway.generate_structured = AsyncMock()
    gateway.health = AsyncMock(return_value={
        "status": "READY",
        "primary_provider": "groq",
        "fallback_provider": "ollama",
        "providers": {"groq": "READY", "ollama": "READY"},
    })
    return gateway

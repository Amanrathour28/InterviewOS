import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestCaseCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    input_data: str = Field(default="")
    expected_output: str = Field(default="")
    explanation: Optional[str] = Field(default="")
    is_hidden: bool = Field(default=False)
    weight: float = Field(default=1.0, ge=0.0)
    order: int = Field(default=0)
    timeout_seconds: float = Field(default=5.0, ge=0.5, le=30.0)


class TestCaseUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    explanation: Optional[str] = None
    is_hidden: Optional[bool] = None
    weight: Optional[float] = None
    order: Optional[int] = None
    timeout_seconds: Optional[float] = None


class TestCaseResponse(BaseModel):
    id: uuid.UUID
    problem_version_id: Optional[uuid.UUID] = None
    title: str
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    explanation: Optional[str] = None
    is_hidden: bool
    weight: float
    order: int
    timeout_seconds: float


class ProblemExample(BaseModel):
    input: str
    output: str
    explanation: Optional[str] = None


class ProblemCreateRequest(BaseModel):
    workspace_id: Optional[uuid.UUID] = None
    title: str = Field(..., max_length=255)
    short_description: str = Field(default="")
    difficulty: str = Field(default="medium")
    category: str = Field(default="algorithms")
    estimated_duration_minutes: int = Field(default=30)
    default_time_limit_seconds: float = Field(default=5.0)
    default_memory_limit_mb: int = Field(default=256)
    tags: List[str] = Field(default_factory=list)
    is_system: bool = Field(default=False)
    problem_statement: str = Field(default="")
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    expected_time_complexity: Optional[str] = None
    expected_space_complexity: Optional[str] = None
    starter_codes: Dict[str, str] = Field(default_factory=dict)
    scoring_policy: Optional[Dict[str, Any]] = None
    test_cases: Optional[List[TestCaseCreateRequest]] = None


class ProblemUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    short_description: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    default_time_limit_seconds: Optional[float] = None
    default_memory_limit_mb: Optional[int] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    problem_statement: Optional[str] = None
    examples: Optional[List[Dict[str, Any]]] = None
    constraints: Optional[List[str]] = None
    expected_time_complexity: Optional[str] = None
    expected_space_complexity: Optional[str] = None
    starter_codes: Optional[Dict[str, str]] = None
    scoring_policy: Optional[Dict[str, Any]] = None


class ProblemCloneRequest(BaseModel):
    target_workspace_id: Optional[uuid.UUID] = None
    new_title: Optional[str] = None


class ProblemVersionResponse(BaseModel):
    id: uuid.UUID
    problem_id: uuid.UUID
    version_number: int
    problem_statement: str
    examples: List[Dict[str, Any]]
    constraints: List[str]
    expected_time_complexity: Optional[str] = None
    expected_space_complexity: Optional[str] = None
    starter_codes: Dict[str, str]
    scoring_policy: Dict[str, Any]
    time_limit_seconds: float
    memory_limit_mb: int
    test_cases: List[TestCaseResponse] = Field(default_factory=list)
    created_at: datetime


class ProblemSummaryResponse(BaseModel):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    title: str
    slug: str
    short_description: str
    difficulty: str
    category: str
    status: str
    estimated_duration_minutes: int
    default_time_limit_seconds: float
    default_memory_limit_mb: int
    tags: List[str]
    is_system: bool
    current_version_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class ProblemDetailResponse(BaseModel):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    title: str
    slug: str
    short_description: str
    difficulty: str
    category: str
    status: str
    estimated_duration_minutes: int
    default_time_limit_seconds: float
    default_memory_limit_mb: int
    tags: List[str]
    is_system: bool
    current_version_id: Optional[uuid.UUID] = None
    current_version: Optional[ProblemVersionResponse] = None
    versions_count: int = 1
    created_at: datetime
    updated_at: datetime


class PaginatedProblemsResponse(BaseModel):
    items: List[ProblemSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProblemAssignRequest(BaseModel):
    problem_id: uuid.UUID
    problem_version_id: Optional[uuid.UUID] = None
    order: Optional[int] = 1


class SessionProblemResponse(BaseModel):
    id: uuid.UUID
    coding_session_id: uuid.UUID
    problem_version_id: uuid.UUID
    order: int
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str
    score: float
    problem: Optional[ProblemSummaryResponse] = None
    version: Optional[ProblemVersionResponse] = None


class ProblemSubmitRequest(BaseModel):
    language: str
    files: Optional[List[Dict[str, Any]]] = None


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    coding_session_id: uuid.UUID
    session_problem_id: Optional[uuid.UUID] = None
    problem_version_id: uuid.UUID
    candidate_id: Optional[uuid.UUID] = None
    submission_number: int
    language: str
    status: str
    score: float
    tests_passed: int
    tests_failed: int
    total_tests: int
    runtime_ms: int
    memory_bytes: int
    submitted_at: datetime
    test_results: Optional[List[Dict[str, Any]]] = None


class AssessmentSummaryResponse(BaseModel):
    id: uuid.UUID
    coding_session_id: uuid.UUID
    problem_version_id: uuid.UUID
    candidate_id: uuid.UUID
    total_submissions: int
    best_score: float
    passed: bool
    evaluation_summary: Dict[str, Any]
    submissions: List[SubmissionResponse] = Field(default_factory=list)
    updated_at: datetime

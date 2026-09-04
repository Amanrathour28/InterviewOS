import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.interview import (
    InterviewDifficulty,
    InterviewStatus,
    InterviewType,
    ParticipantRole,
    QuestionDifficulty,
    QuestionType,
    RoundType,
)


# --- 1. QUESTION SCHEMAS ---

class QuestionBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    prompt: str = Field(..., min_length=5)
    question_type: QuestionType = Field(default=QuestionType.TECHNICAL)
    difficulty: QuestionDifficulty = Field(default=QuestionDifficulty.MEDIUM)
    category: str = Field(default="General", max_length=100)
    expected_duration_minutes: int = Field(default=15, ge=1, le=120)
    skills: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    evaluation_criteria: List[str] = Field(default_factory=list)
    hints: List[str] = Field(default_factory=list)
    reference_answer: Optional[str] = None
    is_template: bool = Field(default=False)


class QuestionCreate(QuestionBase):
    workspace_id: Optional[uuid.UUID] = None


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    prompt: Optional[str] = Field(None, min_length=5)
    question_type: Optional[QuestionType] = None
    difficulty: Optional[QuestionDifficulty] = None
    category: Optional[str] = None
    expected_duration_minutes: Optional[int] = Field(None, ge=1, le=120)
    skills: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    evaluation_criteria: Optional[List[str]] = None
    hints: Optional[List[str]] = None
    reference_answer: Optional[str] = None
    is_template: Optional[bool] = None


class QuestionResponse(QuestionBase):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedQuestionsResponse(BaseModel):
    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- 2. ROUND QUESTION SCHEMAS ---

class RoundQuestionCreate(BaseModel):
    question_id: uuid.UUID
    sequence: Optional[int] = None
    is_required: bool = True
    time_limit_seconds: Optional[int] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)


class RoundQuestionResponse(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID
    question_id: uuid.UUID
    sequence: int
    is_required: bool
    time_limit_seconds: Optional[int] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    question: Optional[QuestionResponse] = None
    model_config = ConfigDict(from_attributes=True)


class ReorderItem(BaseModel):
    id: uuid.UUID
    sequence: int


class ReorderRequest(BaseModel):
    items: List[ReorderItem]


# --- 3. INTERVIEW ROUND SCHEMAS ---

class RoundBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    round_type: RoundType = Field(default=RoundType.TECHNICAL)
    sequence: int = Field(default=1, ge=1)
    duration_minutes: int = Field(default=30, ge=1, le=240)
    difficulty: InterviewDifficulty = Field(default=InterviewDifficulty.MID)
    instructions: Optional[str] = None
    is_required: bool = Field(default=True)
    configuration: Dict[str, Any] = Field(default_factory=dict)


class RoundCreate(RoundBase):
    pass


class RoundUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    round_type: Optional[RoundType] = None
    sequence: Optional[int] = Field(None, ge=1)
    duration_minutes: Optional[int] = Field(None, ge=1, le=240)
    difficulty: Optional[InterviewDifficulty] = None
    instructions: Optional[str] = None
    is_required: Optional[bool] = None
    configuration: Optional[Dict[str, Any]] = None


class RoundResponse(RoundBase):
    id: uuid.UUID
    interview_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    questions: List[RoundQuestionResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# --- 4. PARTICIPANT SCHEMAS ---

class ParticipantCreate(BaseModel):
    user_id: uuid.UUID
    participant_role: ParticipantRole = Field(default=ParticipantRole.INTERVIEWER)
    is_primary: bool = Field(default=False)


class ParticipantResponse(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    user_id: uuid.UUID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    participant_role: ParticipantRole
    is_primary: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- 5. TEMPLATE SCHEMAS ---

class TemplateRoundCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    round_type: RoundType = Field(default=RoundType.TECHNICAL)
    sequence: int = Field(default=1, ge=1)
    duration_minutes: int = Field(default=30, ge=1)
    difficulty: InterviewDifficulty = Field(default=InterviewDifficulty.MID)
    instructions: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    question_ids: List[uuid.UUID] = Field(default_factory=list)


class TemplateCreate(BaseModel):
    workspace_id: Optional[uuid.UUID] = None
    name: str = Field(..., min_length=2, max_length=200)
    description: str = Field(default="")
    interview_type: InterviewType = Field(default=InterviewType.TECHNICAL)
    difficulty: InterviewDifficulty = Field(default=InterviewDifficulty.MID)
    total_duration_minutes: int = Field(default=60, ge=1)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    rounds: List[TemplateRoundCreate] = Field(default_factory=list)


class TemplateRoundResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    round_type: RoundType
    sequence: int
    duration_minutes: int
    difficulty: InterviewDifficulty
    instructions: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(from_attributes=True)


class TemplateResponse(BaseModel):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID]
    name: str
    description: str
    interview_type: InterviewType
    difficulty: InterviewDifficulty
    total_duration_minutes: int
    is_system: bool
    configuration: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    rounds: List[TemplateRoundResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class PaginatedTemplatesResponse(BaseModel):
    items: List[TemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- 6. INTERVIEW SCHEMAS ---

class InterviewBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(default="")
    interview_type: InterviewType = Field(default=InterviewType.TECHNICAL)
    difficulty: InterviewDifficulty = Field(default=InterviewDifficulty.MID)
    duration_minutes: int = Field(default=60, ge=1, le=480)
    timezone: str = Field(default="UTC", max_length=50)
    instructions: Optional[str] = None
    candidate_instructions: Optional[str] = None
    interviewer_instructions: Optional[str] = None


class InterviewCreate(InterviewBase):
    workspace_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    initial_rounds: Optional[List[RoundCreate]] = None


class InterviewFromTemplateCreate(BaseModel):
    workspace_id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    title: Optional[str] = None


class InterviewUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    interview_type: Optional[InterviewType] = None
    status: Optional[InterviewStatus] = None
    difficulty: Optional[InterviewDifficulty] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    timezone: Optional[str] = None
    instructions: Optional[str] = None
    candidate_instructions: Optional[str] = None
    interviewer_instructions: Optional[str] = None
    job_id: Optional[uuid.UUID] = None


class InterviewResponse(InterviewBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    status: InterviewStatus
    round_count: int = 0
    participant_count: int = 0
    is_ready: bool = False
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InterviewReadinessResponse(BaseModel):
    interview_id: uuid.UUID
    is_ready: bool
    current_status: InterviewStatus
    issues: List[str] = Field(default_factory=list)


class InterviewDetailResponse(InterviewResponse):
    rounds: List[RoundResponse] = Field(default_factory=list)
    participants: List[ParticipantResponse] = Field(default_factory=list)
    readiness: InterviewReadinessResponse


class PaginatedInterviewsResponse(BaseModel):
    items: List[InterviewResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

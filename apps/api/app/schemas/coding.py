import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CodingFileCreateRequest(BaseModel):
    path: str = Field(..., max_length=255, description="Relative safe file path, e.g., 'solution.py' or 'src/utils.py'")
    name: str = Field(..., max_length=128, description="File name, e.g., 'solution.py'")
    language: str = Field(default="python", max_length=32)
    content: Optional[str] = Field(default="", description="Initial content")


class CodingFileUpdateRequest(BaseModel):
    path: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=128)
    content: Optional[str] = None
    is_active: Optional[bool] = None


class CodingFileResponse(BaseModel):
    id: uuid.UUID
    coding_session_id: uuid.UUID
    path: str
    name: str
    language: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CodingSnapshotCreateRequest(BaseModel):
    reason: str = Field(default="manual", description="Snapshot reason")
    files: List[Dict[str, Any]] = Field(default_factory=list)


class CodingSnapshotResponse(BaseModel):
    id: uuid.UUID
    coding_session_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    reason: str
    files: List[Dict[str, Any]]
    created_at: datetime


class CodingTestCaseCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    input_data: str = Field(default="")
    expected_output: str = Field(default="")
    is_hidden: bool = Field(default=False)
    timeout_seconds: float = Field(default=5.0, ge=0.5, le=30.0)


class CodingTestCaseResponse(BaseModel):
    id: uuid.UUID
    coding_session_id: uuid.UUID
    title: str
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    is_hidden: bool
    timeout_seconds: float


class TestResultItem(BaseModel):
    test_id: Optional[str] = None
    title: str
    passed: bool
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    stdout: Optional[str] = None
    is_hidden: bool = False


class CodingExecutionResultResponse(BaseModel):
    id: uuid.UUID
    execution_job_id: uuid.UUID
    status: str
    exit_code: Optional[int] = None
    stdout: str
    stderr: str
    compile_output: Optional[str] = None
    duration_ms: Optional[int] = None
    memory_bytes: Optional[int] = None
    tests_passed: int
    tests_failed: int
    test_results: List[TestResultItem]
    created_at: datetime


class CodingExecutionJobResponse(BaseModel):
    id: uuid.UUID
    coding_session_id: uuid.UUID
    requested_by: Optional[uuid.UUID] = None
    snapshot_id: uuid.UUID
    status: str
    language: str
    is_submission: bool
    custom_input: Optional[str] = None
    result: Optional[CodingExecutionResultResponse] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CodingExecutionRequest(BaseModel):
    language: str = Field(default="python", max_length=32)
    files: Optional[List[Dict[str, Any]]] = Field(None, description="Current workspace files state")
    is_submission: bool = Field(default=False)
    custom_input: Optional[str] = Field(None, max_length=100000)


class EditorLockRequest(BaseModel):
    is_locked: bool = Field(..., description="True to lock candidate editor, False to unlock")


class CodingSessionResponse(BaseModel):
    id: uuid.UUID
    interview_session_id: uuid.UUID
    workspace_id: uuid.UUID
    problem_id: Optional[uuid.UUID] = None
    language: str
    active_file_id: Optional[uuid.UUID] = None
    status: str
    is_editor_locked: bool
    settings: Dict[str, Any]
    files: List[CodingFileResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.candidate import CandidateSource, CandidateStatus, DocumentType


# 1. Candidate Tags
class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#6366f1", max_length=20)


class TagCreate(TagBase):
    workspace_id: uuid.UUID


class TagResponse(TagBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 2. Candidate Notes
class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1)


class NoteResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    author_id: Optional[uuid.UUID]
    author_name: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 3. Candidate Documents
class DocumentResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    uploaded_by: Optional[uuid.UUID]
    file_name: str
    mime_type: str
    file_size: int
    document_type: DocumentType
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 4. Candidate Activity Timeline
class ActivityResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    actor_name: Optional[str] = None
    event_type: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 5. Candidate Job Applications
class JobApplicationCreate(BaseModel):
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    status: CandidateStatus = Field(default=CandidateStatus.NEW)
    source: Optional[str] = None


class JobApplicationUpdate(BaseModel):
    status: CandidateStatus


class JobApplicationResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    job_title: Optional[str] = None
    job_department: Optional[str] = None
    candidate_id: uuid.UUID
    status: CandidateStatus
    source: Optional[str] = None
    applied_at: datetime
    last_activity_at: datetime
    model_config = ConfigDict(from_attributes=True)


# 6. Candidate Schemas
class CandidateBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=150)
    headline: Optional[str] = Field(None, max_length=255)
    current_company: Optional[str] = Field(None, max_length=150)
    current_title: Optional[str] = Field(None, max_length=150)
    experience_years: Optional[float] = Field(None, ge=0)
    education_summary: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    status: CandidateStatus = Field(default=CandidateStatus.NEW)
    source: CandidateSource = Field(default=CandidateSource.INBOUND)
    notes_summary: Optional[str] = None


class CandidateCreate(CandidateBase):
    workspace_id: uuid.UUID
    tag_names: Optional[List[str]] = None
    job_id: Optional[uuid.UUID] = None  # Optionally apply immediately to a job


class CandidateUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    current_company: Optional[str] = None
    current_title: Optional[str] = None
    experience_years: Optional[float] = None
    education_summary: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    status: Optional[CandidateStatus] = None
    source: Optional[CandidateSource] = None
    notes_summary: Optional[str] = None


class CandidateResponse(CandidateBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = Field(default_factory=list)
    job_applications: List[JobApplicationResponse] = Field(default_factory=list)
    document_count: int = 0
    note_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PaginatedCandidatesResponse(BaseModel):
    items: List[CandidateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.job import EmploymentType, JobPriority, JobStatus


class JobBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(default="")
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=150)
    employment_type: EmploymentType = Field(default=EmploymentType.FULL_TIME)
    experience_min: Optional[int] = Field(None, ge=0, le=50)
    experience_max: Optional[int] = Field(None, ge=0, le=50)
    status: JobStatus = Field(default=JobStatus.OPEN)
    priority: JobPriority = Field(default=JobPriority.MEDIUM)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=10)


class JobCreate(JobBase):
    workspace_id: uuid.UUID
    slug: Optional[str] = None


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[EmploymentType] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    status: Optional[JobStatus] = None
    priority: Optional[JobPriority] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class JobResponse(JobBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    candidate_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PaginatedJobsResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

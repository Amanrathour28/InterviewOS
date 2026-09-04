import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.organization import OrgMemberRole


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    logo_url: Optional[str] = Field(None, max_length=1024)


class OrganizationCreate(OrganizationBase):
    initial_workspace_name: Optional[str] = Field("Default", min_length=1, max_length=100)


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    created_at: datetime
    role: Optional[OrgMemberRole] = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: Optional[str] = None


class OrganizationWithWorkspacesResponse(OrganizationResponse):
    workspaces: List[WorkspaceSummary] = []

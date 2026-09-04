import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.workspace import WorkspaceMemberRole


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)


class WorkspaceCreate(WorkspaceBase):
    organization_id: uuid.UUID


class WorkspaceResponse(WorkspaceBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    role: Optional[WorkspaceMemberRole] = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceSwitchRequest(BaseModel):
    workspace_id: uuid.UUID

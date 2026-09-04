import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WhiteboardUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    document: Optional[Dict[str, Any]] = None
    private_layer: Optional[Dict[str, Any]] = None


class WhiteboardLockRequest(BaseModel):
    is_locked: bool


class WhiteboardSnapshotCreateRequest(BaseModel):
    label: Optional[str] = Field("Milestone Checkpoint", max_length=255)
    source: Optional[str] = Field("manual", max_length=32)


class WhiteboardSnapshotResponse(BaseModel):
    id: uuid.UUID
    whiteboard_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    snapshot_number: int
    label: str
    source: str
    document: Dict[str, Any]
    private_layer: Optional[Dict[str, Any]] = None
    created_at: datetime


class WhiteboardResponse(BaseModel):
    id: uuid.UUID
    interview_session_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    is_locked: bool
    document: Dict[str, Any]
    private_layer: Optional[Dict[str, Any]] = None
    created_by: Optional[uuid.UUID] = None
    snapshots: List[WhiteboardSnapshotResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

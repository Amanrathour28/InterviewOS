import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.session import NoteCategory, SessionStage, SessionStatus


class SessionCreate(BaseModel):
    pass


class SessionActionRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=255)


class StageChangeRequest(BaseModel):
    stage: str = Field(..., max_length=64, description="Target stage name")
    reason: Optional[str] = Field(None, max_length=255)


class InterviewerNoteCreate(BaseModel):
    category: NoteCategory = NoteCategory.GENERAL
    stage: Optional[str] = None
    content: str = Field(..., min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)
    tags: List[str] = Field(default_factory=list)


class InterviewerNoteUpdate(BaseModel):
    category: Optional[NoteCategory] = None
    stage: Optional[str] = None
    content: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[List[str]] = None


class InterviewerNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    author_name: Optional[str] = None
    category: NoteCategory
    stage: Optional[str] = None
    content: str
    rating: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    event_type: str
    actor_id: Optional[uuid.UUID] = None
    actor_role: str
    sequence: int
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SessionTimelineItemResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    category: str
    title: str
    actor_name: str
    actor_role: str
    timestamp: datetime
    sequence: int
    payload: Dict[str, Any] = Field(default_factory=dict)


class JoinTokenResponse(BaseModel):
    token: str
    session_id: uuid.UUID
    room_id: str
    role: str
    user_id: uuid.UUID
    user_name: str
    is_interviewer: bool
    expires_in_seconds: int
    realtime_url: str
    ice_servers: List[Dict[str, Any]] = Field(default_factory=list)


class SessionParticipant(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: str
    is_primary: bool = False
    is_online: bool = False
    camera_enabled: bool = True
    microphone_enabled: bool = True
    screen_sharing: bool = False


class SessionHealthResponse(BaseModel):
    session_id: uuid.UUID
    status: SessionStatus
    is_operational: bool
    active_participants_count: int
    websocket_healthy: bool = True
    webrtc_healthy: bool = True
    system_warnings: List[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_id: uuid.UUID
    workspace_id: uuid.UUID
    status: SessionStatus
    current_stage: str
    stage_started_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    total_paused_seconds: int = 0
    last_event_sequence: int = 0
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class SessionDetailResponse(SessionResponse):
    interview_title: str
    candidate_id: uuid.UUID
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    duration_minutes: int
    current_elapsed_seconds: int = 0
    remaining_seconds: int = 0
    stage_elapsed_seconds: int = 0
    is_paused: bool = False
    is_interviewer: bool = False
    participants: List[SessionParticipant] = []


class CandidateWaitingRoomResponse(BaseModel):
    session_id: uuid.UUID
    interview_id: uuid.UUID
    interview_title: str
    workspace_name: str
    scheduled_at: Optional[datetime] = None
    duration_minutes: int
    instructions: Optional[str] = None
    status: SessionStatus
    candidate_name: str
    ice_servers: List[Dict[str, Any]] = Field(default_factory=list)


class RoomStateResponse(BaseModel):
    session_id: uuid.UUID
    interview_id: uuid.UUID
    workspace_id: uuid.UUID
    status: SessionStatus
    current_stage: str
    stage_started_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    elapsed_seconds: int = 0
    remaining_seconds: int = 0
    stage_elapsed_seconds: int = 0
    is_paused: bool = False
    last_event_sequence: int = 0
    participants: List[SessionParticipant] = []

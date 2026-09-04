import uuid
from datetime import datetime, time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.scheduling import InvitationStatus, NotificationType, RecipientType, ScheduleStatus


# --- 1. SCHEDULE SCHEMAS ---

class ScheduleCreate(BaseModel):
    scheduled_start_at: datetime = Field(..., description="Start timestamp (will be stored canonically in UTC)")
    timezone: str = Field("UTC", description="IANA timezone identifier, e.g. Asia/Kolkata")


class ScheduleReschedule(BaseModel):
    scheduled_start_at: datetime = Field(..., description="New start timestamp")
    timezone: str = Field("UTC", description="New IANA timezone identifier")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for rescheduling")


class ScheduleCancel(BaseModel):
    cancellation_reason: Optional[str] = Field("cancelled", max_length=255)


class ScheduleHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    schedule_id: uuid.UUID
    previous_start_at: datetime
    previous_end_at: datetime
    previous_timezone: str
    new_start_at: datetime
    new_end_at: datetime
    new_timezone: str
    changed_by: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    created_at: datetime


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_id: uuid.UUID
    workspace_id: uuid.UUID
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    timezone: str
    status: ScheduleStatus
    created_by: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[uuid.UUID] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    history: List[ScheduleHistoryResponse] = []


# --- 2. AVAILABILITY SCHEMAS ---

class UserAvailabilityCreate(BaseModel):
    user_id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time
    end_time: time
    timezone: str = Field("UTC", description="IANA timezone")
    is_active: bool = True


class UserAvailabilityUpdate(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class UserAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AvailabilityExceptionCreate(BaseModel):
    workspace_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    start_at: datetime
    end_at: datetime
    exception_type: str = "leave"
    reason: Optional[str] = None


class AvailabilityExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    exception_type: str
    reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# --- 3. AVAILABLE SLOTS SCHEMAS ---

class AvailableSlot(BaseModel):
    start_at: datetime
    end_at: datetime
    duration_minutes: int


class AvailableSlotsResponse(BaseModel):
    requested_date: str
    timezone: str
    duration_minutes: int
    slots: List[AvailableSlot]


# --- 4. INVITATION SCHEMAS ---

class InvitationCreate(BaseModel):
    recipient_type: RecipientType
    email: EmailStr
    recipient_user_id: Optional[uuid.UUID] = None
    recipient_candidate_id: Optional[uuid.UUID] = None


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_id: uuid.UUID
    workspace_id: uuid.UUID
    recipient_type: RecipientType
    email: str
    status: InvitationStatus
    expires_at: datetime
    sent_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    created_at: datetime


class PublicInvitationDetail(BaseModel):
    interview_id: uuid.UUID
    title: str
    description: Optional[str] = None
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    timezone: str
    duration_minutes: int
    candidate_name: Optional[str] = None
    job_title: Optional[str] = None
    interviewer_names: List[str] = []
    status: InvitationStatus
    expires_at: datetime


class InvitationActionRequest(BaseModel):
    reason: Optional[str] = None


# --- 5. NOTIFICATION SCHEMAS ---

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    notification_type: NotificationType
    title: str
    message: str
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)
    read_at: Optional[datetime] = None
    created_at: datetime


# --- 6. CALENDAR EVENT SCHEMAS ---

class CalendarEvent(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    candidate_id: uuid.UUID
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    timezone: str
    status: ScheduleStatus
    interview_status: str
    interview_type: str
    duration_minutes: int
    participant_count: int

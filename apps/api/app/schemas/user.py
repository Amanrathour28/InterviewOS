import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=150)
    avatar_url: Optional[str] = Field(None, max_length=1024)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role: Optional[UserRole] = Field(default=UserRole.CANDIDATE)


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=150)
    avatar_url: Optional[str] = Field(None, max_length=1024)


class UserResponse(UserBase):
    id: uuid.UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MembershipSummary(BaseModel):
    id: uuid.UUID
    target_id: uuid.UUID
    name: str
    slug: str
    role: str


class UserProfileResponse(UserResponse):
    organizations: List[MembershipSummary] = []
    workspaces: List[MembershipSummary] = []

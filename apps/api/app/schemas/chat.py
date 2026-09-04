import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_CODE_LANGUAGES = [
    "python",
    "javascript",
    "typescript",
    "java",
    "c",
    "cpp",
    "go",
    "rust",
    "sql",
    "bash",
    "json",
    "yaml",
    "html",
    "css",
]

ALLOWED_REACTIONS = ["👍", "❤️", "😂", "🎯", "👏", "❓"]


class CodeSnippetPayload(BaseModel):
    language: str = Field(..., description="Programming language identifier")
    code: str = Field(..., max_length=50000, description="Source code text")
    title: Optional[str] = Field(None, max_length=200, description="Optional snippet title")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in SUPPORTED_CODE_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{v}'. Supported: {', '.join(SUPPORTED_CODE_LANGUAGES)}"
            )
        return clean


class MessageCreateRequest(BaseModel):
    message_type: str = Field("text", description="'text' or 'code'")
    content: str = Field(..., max_length=50000, description="Message text or code content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    parent_message_id: Optional[uuid.UUID] = None
    client_message_id: Optional[str] = Field(None, max_length=64)

    @field_validator("message_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("text", "code", "system"):
            raise ValueError("message_type must be 'text', 'code', or 'system'")
        return v

    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v: str, info) -> str:
        msg_type = info.data.get("message_type", "text")
        if msg_type == "text" and len(v) > 8000:
            raise ValueError("Text message content cannot exceed 8,000 characters")
        if msg_type == "code" and len(v) > 50000:
            raise ValueError("Code snippet content cannot exceed 50,000 characters")
        return v


class MessageEditRequest(BaseModel):
    content: str = Field(..., max_length=50000)
    metadata: Optional[Dict[str, Any]] = None


class ReactionRequest(BaseModel):
    emoji: str = Field(..., max_length=16)

    @field_validator("emoji")
    @classmethod
    def validate_emoji(cls, v: str) -> str:
        clean = v.strip()
        if clean not in ALLOWED_REACTIONS:
            raise ValueError(f"Unsupported reaction '{v}'. Allowed: {', '.join(ALLOWED_REACTIONS)}")
        return clean


class ReadCursorRequest(BaseModel):
    last_read_message_id: uuid.UUID


class ChatReactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    emoji: str
    created_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel_id: uuid.UUID
    session_id: uuid.UUID
    workspace_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    sender_name: str
    sender_role: str
    parent_message_id: Optional[uuid.UUID] = None
    message_type: str
    content: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict, alias="metadata")
    client_message_id: Optional[str] = None
    is_edited: bool = False
    is_deleted: bool = False
    reply_count: int = 0
    reactions: List[ChatReactionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChatChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    workspace_id: uuid.UUID
    channel_type: str
    name: str
    unread_count: int = 0
    created_at: datetime


class ThreadDetailResponse(BaseModel):
    parent_message: ChatMessageResponse
    replies: List[ChatMessageResponse] = Field(default_factory=list)


class UnreadCountResponse(BaseModel):
    channel_id: uuid.UUID
    channel_type: str
    unread_count: int

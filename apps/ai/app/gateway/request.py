"""
Standard AI Request / Response schemas.

Provider-specific response objects must NEVER leak into business logic.
All agent code works exclusively with AIRequest and AIResponse.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class AIMessage(BaseModel):
    """A single message in a conversation context."""

    role: str  # "system" | "user" | "assistant"
    content: str


class AIRequest(BaseModel):
    """
    Standard internal AI request.
    Created by agents, consumed by the AIGateway.
    """

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Provider overrides (if None, gateway uses configured defaults)
    provider: Optional[str] = None
    model: Optional[str] = None

    # Prompt content
    system_prompt: str
    messages: List[AIMessage]

    # Generation parameters
    temperature: float = 0.3
    max_tokens: int = 2048

    # Structured output: if set, gateway validates response against this Pydantic schema
    response_schema: Optional[Any] = None  # Type[BaseModel]
    response_schema_name: Optional[str] = None

    # Request config
    timeout_seconds: int = 30
    max_retries: int = 3

    # Observability metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    workspace_id: Optional[str] = None
    interview_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_name: Optional[str] = None
    task_type: Optional[str] = None
    prompt_name: Optional[str] = None
    prompt_version: Optional[str] = None


class AIUsage(BaseModel):
    """Token usage reported by the provider."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class AIResponse(BaseModel):
    """
    Standard internal AI response.
    Provider-specific fields are normalized into this structure.
    """

    request_id: str

    # Which provider/model actually served this response
    provider: str
    model: str

    # Raw text content (always populated)
    content: str

    # Parsed structured output (populated if request had response_schema)
    structured_output: Optional[Any] = None

    # Usage stats
    usage: AIUsage = Field(default_factory=AIUsage)

    # Performance
    latency_ms: int = 0

    # Generation metadata
    finish_reason: Optional[str] = None

    # Whether this came from a fallback provider
    is_fallback: bool = False

    # Retry count used to produce this response
    retry_count: int = 0

    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Passthrough metadata from request
    metadata: Dict[str, Any] = Field(default_factory=dict)

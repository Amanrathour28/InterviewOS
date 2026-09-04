"""
AIRequestLog Model — Telemetry for AI requests.

Tracks every AI request made through the AI service.
Does NOT store raw prompt or response content (privacy).
Used for observability, cost tracking, and audit.
"""

import uuid
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone

from app.models.base import Base


class AIRequestLog(Base):
    """
    Persistent log entry for AI service requests.
    Written by the AI service telemetry module.
    Readable by the API service for reporting.
    """

    __tablename__ = "ai_request_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(String(36), nullable=False, index=True)

    # Tenant context (not FK — AI service may run independently)
    workspace_id = Column(String(36), nullable=True, index=True)
    interview_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), nullable=True)

    # Agent identity
    agent_name = Column(String(100), nullable=True)
    task_type = Column(String(100), nullable=True)
    prompt_name = Column(String(100), nullable=True)
    prompt_version = Column(String(20), nullable=True)

    # Provider
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    is_fallback = Column(Boolean, default=False)

    # Token usage
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Performance
    latency_ms = Column(Integer, default=0)

    # Outcome
    success = Column(Boolean, nullable=False)
    error_type = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_ai_request_logs_workspace_created", "workspace_id", "created_at"),
        Index("ix_ai_request_logs_interview_created", "interview_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AIRequestLog id={self.id} agent={self.agent_name} "
            f"provider={self.provider} success={self.success}>"
        )

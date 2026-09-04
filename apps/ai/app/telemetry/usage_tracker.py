"""
AI Usage Tracker — Persistent telemetry for AI requests.

Writes to the ai_request_logs table (created by migration 011).
Tracks: provider, model, tokens, latency, success/failure, agent, task.

Privacy: raw prompt/response content is NOT stored by default.
Only metadata, usage stats, and structured results are persisted.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings

logger = logging.getLogger("interviewos.ai.telemetry")

# Lazy database session — only created if AI_LOG_REQUESTS is True
_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=2,
        )
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def log_request(
    request_id: str,
    workspace_id: Optional[str],
    interview_id: Optional[str],
    user_id: Optional[str],
    agent_name: Optional[str],
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    latency_ms: int,
    success: bool,
    error_type: Optional[str] = None,
    prompt_name: Optional[str] = None,
    prompt_version: Optional[str] = None,
    task_type: Optional[str] = None,
    is_fallback: bool = False,
) -> None:
    """
    Persist an AI request log entry.
    Silently handles failures — telemetry must never crash the AI pipeline.
    """
    if not settings.AI_LOG_REQUESTS:
        return

    try:
        session_factory = _get_session_factory()
        async with session_factory() as session:
            await session.execute(
                sa.text("""
                    INSERT INTO ai_request_logs (
                        id, request_id, workspace_id, interview_id, user_id,
                        agent_name, provider, model,
                        input_tokens, output_tokens, total_tokens,
                        latency_ms, success, error_type,
                        prompt_name, prompt_version, task_type, is_fallback,
                        created_at
                    ) VALUES (
                        :id, :request_id, :workspace_id, :interview_id, :user_id,
                        :agent_name, :provider, :model,
                        :input_tokens, :output_tokens, :total_tokens,
                        :latency_ms, :success, :error_type,
                        :prompt_name, :prompt_version, :task_type, :is_fallback,
                        :created_at
                    )
                """),
                {
                    "id": str(uuid.uuid4()),
                    "request_id": request_id,
                    "workspace_id": workspace_id,
                    "interview_id": interview_id,
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "provider": provider,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "latency_ms": latency_ms,
                    "success": success,
                    "error_type": error_type,
                    "prompt_name": prompt_name,
                    "prompt_version": prompt_version,
                    "task_type": task_type,
                    "is_fallback": is_fallback,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            await session.commit()

        logger.debug(
            "AI request logged: %s provider=%s model=%s tokens=%d success=%s",
            request_id[:8], provider, model, total_tokens, success,
        )
    except Exception as exc:
        # Telemetry failure must never crash the AI pipeline
        logger.warning("Failed to write AI request log: %s", exc)

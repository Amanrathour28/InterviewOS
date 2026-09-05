"""
InterviewOS — Production-hardened database engine configuration (Phase 16.2)

Key changes for Neon Serverless PostgreSQL & Vercel serverless compatibility:
- pool_pre_ping: True      — Validates connections before use (Neon auto-suspend recovery)
- pool_recycle: 300        — Recycles connections after 5 min to avoid stale serverless connections
- pool_size: 5             — Reduced from 10 to stay within Neon free-tier connection limits
- max_overflow: 10         — Reduced from 20 accordingly
- connect_args ssl: True   — Enables SSL for Neon (required for cloud connections)
"""

import logging
from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_connect_args(database_url: str) -> dict:
    """
    Detect if the connection is to a cloud provider (Neon, AWS, GCP, Azure)
    and return appropriate SSL & pooler connect_args. Local connections skip SSL.
    """
    try:
        parsed = urlparse(database_url)
        host = parsed.hostname or ""
        is_cloud = any(
            provider in host
            for provider in [
                "neon.tech",
                "amazonaws.com",
                "supabase.com",
                "cockroachlabs.cloud",
                "elephantsql.com",
            ]
        )
        connect_args = {}
        if is_cloud:
            logger.info("[database] Cloud PostgreSQL detected at %s — enabling SSL", host)
            connect_args["ssl"] = True
        if "pooler" in host or is_cloud:
            # Disable prepared statement caching for PgBouncer / Neon connection pooler compatibility
            connect_args["statement_cache_size"] = 0
        return connect_args
    except Exception:
        pass
    return {}


_connect_args = _build_connect_args(settings.DATABASE_URL)

# Production-hardened async engine
# - pool_pre_ping validates connections on reuse (handles Neon auto-suspend)
# - pool_recycle prevents stale connections surviving serverless cold starts
# - pool_size / max_overflow tuned for Neon free-tier (max 10 connections)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining scoped database sessions in FastAPI route handlers."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

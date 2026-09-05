import time
from datetime import datetime, timezone
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthResponse, ServiceStatus

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Health Check",
    description="Inspects the operational status of the API, PostgreSQL database, and Redis cache.",
)
async def check_health(db: AsyncSession = Depends(get_db)):
    services = {}
    overall_status = "healthy"

    # Check Database
    t0 = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - t0) * 1000, 2)
        services["database"] = ServiceStatus(status="healthy", latency_ms=latency)
    except Exception as exc:
        overall_status = "unhealthy"
        services["database"] = ServiceStatus(
            status="unavailable",
            detail=f"Database connection error: {str(exc)}",
        )

    # Check Redis
    t0 = time.perf_counter()
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        await r.ping()
        await r.aclose()
        latency = round((time.perf_counter() - t0) * 1000, 2)
        services["redis"] = ServiceStatus(status="healthy", latency_ms=latency)
    except Exception as exc:
        if overall_status == "healthy":
            overall_status = "degraded"
        services["redis"] = ServiceStatus(
            status="unavailable",
            detail=f"Redis connection error: {str(exc)}",
        )

    response_payload = HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version=__version__,
        timestamp=datetime.now(timezone.utc),
        services=services,
    )

    http_status = status.HTTP_200_OK if overall_status in ("healthy", "degraded") else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=response_payload.model_dump(mode="json"))

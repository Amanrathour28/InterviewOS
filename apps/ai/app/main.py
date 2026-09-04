"""
InterviewOS AI Service — FastAPI Application Entry Point.

This is a standalone micro-service for AI orchestration.
It does NOT replace any existing service.

Architecture:
  apps/api/  ← Main API (auth, sessions, coding, whiteboard)
  apps/ai/   ← AI Gateway + Agents (this service)
  apps/realtime/ ← Socket.IO gateway
  apps/web/  ← Next.js frontend
"""

import time
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app import __version__
from app.config import settings
from app.api.v1.router import api_router
# Import prompts to trigger registration
import app.prompts  # noqa: F401

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s",
)
logger = logging.getLogger("interviewos.ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (version: %s, env: %s, provider: %s)",
        settings.APP_NAME, __version__, settings.APP_ENV, settings.AI_PROVIDER,
    )
    # Eagerly initialize the gateway to catch config errors at startup
    from app.gateway.ai_gateway import get_gateway
    gateway = get_gateway()
    logger.info("AIGateway initialized: primary=%s fallback=%s", gateway._primary, gateway._fallback)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title="InterviewOS AI Gateway",
    description="Provider-agnostic AI Gateway + Multi-Agent Intelligence for InterviewOS",
    version=__version__,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan,
)

# CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Request ID + Latency middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time * 1000:.2f}ms"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Invalid request payload",
            "details": exc.errors(),
        },
    )


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": __version__,
        "provider": settings.AI_PROVIDER,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health",
    }

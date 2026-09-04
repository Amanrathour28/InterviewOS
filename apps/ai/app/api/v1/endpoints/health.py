"""
AI Service Health Endpoint.

Returns the status of all AI providers and the graph.
Never exposes API keys or internal credentials.
"""

import logging
from fastapi import APIRouter

from app.gateway.ai_gateway import get_gateway

logger = logging.getLogger("interviewos.ai.api.health")
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    AI service health check.

    Returns provider status without exposing credentials.
    States: READY | DEGRADED | UNAVAILABLE | MISCONFIGURED
    """
    gateway = get_gateway()
    health_data = await gateway.health()

    return {
        "service": "interviewos-ai",
        "status": health_data["status"],
        "providers": health_data["providers"],
        "primary_provider": health_data["primary_provider"],
        "fallback_provider": health_data["fallback_provider"],
        "graph": "READY",
    }

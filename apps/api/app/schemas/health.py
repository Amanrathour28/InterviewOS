from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    status: str = Field(..., description="Status of the sub-service (e.g., 'healthy', 'degraded', 'unavailable')")
    latency_ms: Optional[float] = Field(None, description="Latency in milliseconds")
    detail: Optional[str] = Field(None, description="Additional context or error message")


class HealthResponse(BaseModel):
    status: str = Field("healthy", description="Overall health of the application")
    app_name: str
    environment: str
    version: str
    timestamp: datetime
    services: Dict[str, ServiceStatus]

"""
AI Service Configuration.
Mirrors the InterviewOS API config pattern (pydantic_settings.BaseSettings).
All secrets come from environment variables — never hardcoded.
"""

from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General
    APP_NAME: str = "InterviewOS-AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    AI_SERVICE_PORT: int = 8001
    API_V1_STR: str = "/api/v1"

    # JWT — must match the API service secret for token validation
    SECRET_KEY: str = "dev-secret-key-32-chars-interviewos-platform-security"

    # CORS — allow the main API and frontend
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        import json
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return v

    # Database — same as API service for AIRequestLog persistence
    DATABASE_URL: str = (
        "postgresql+asyncpg://interviewos:interviewos_secret@localhost:5432/interviewos_db"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            return v
        cleaned = v.strip()
        if cleaned.startswith("postgres://"):
            cleaned = "postgresql+asyncpg://" + cleaned[len("postgres://"):]
        elif cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+asyncpg://"):
            cleaned = "postgresql+asyncpg://" + cleaned[len("postgresql://"):]
        if "sslmode=require" in cleaned:
            cleaned = cleaned.replace("sslmode=require", "ssl=require")
        return cleaned

    # Redis — for locking, caching, pub/sub
    REDIS_URL: str = "redis://localhost:6379/0"

    # -----------------------------------------------------------------------
    # AI Provider Configuration
    # -----------------------------------------------------------------------

    # Primary provider: "groq" | "ollama"
    AI_PROVIDER: str = "groq"

    # Fallback provider (used when primary fails with retryable error)
    AI_FALLBACK_PROVIDER: str = "ollama"

    # Groq — primary remote provider (free tier available)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Groq — smaller/faster model for simple extraction tasks
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"

    # Ollama — local fallback (zero cost, runs locally)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # -----------------------------------------------------------------------
    # AI Behaviour Configuration
    # -----------------------------------------------------------------------

    # Request timeout in seconds per provider call
    AI_TIMEOUT_SECONDS: int = 30

    # Maximum retry attempts before failing (does not retry non-retryable errors)
    AI_MAX_RETRIES: int = 3

    # Default generation temperature (0.0 = deterministic, 1.0 = creative)
    AI_TEMPERATURE: float = 0.3

    # Low-temperature mode for deterministic extraction tasks
    AI_EXTRACTION_TEMPERATURE: float = 0.1

    # Maximum output tokens per request
    AI_MAX_TOKENS: int = 2048

    # Structured output mode: "json_schema" | "function_calling"
    AI_STRUCTURED_OUTPUT_MODE: str = "json_schema"

    # -----------------------------------------------------------------------
    # Context & Privacy Configuration
    # -----------------------------------------------------------------------

    # Maximum number of recent events to include in context
    AI_MAX_CONTEXT_EVENTS: int = 50

    # Maximum characters of raw candidate content to include
    AI_MAX_CANDIDATE_CONTENT_CHARS: int = 8000

    # Maximum characters of prompt payload before truncation
    AI_MAX_PROMPT_CHARS: int = 16000

    # -----------------------------------------------------------------------
    # Rate Limiting
    # -----------------------------------------------------------------------

    # Per-workspace AI requests per minute
    AI_RATE_LIMIT_WORKSPACE: int = 60

    # Per-user AI requests per minute
    AI_RATE_LIMIT_USER: int = 30

    # Per-interview AI requests per minute
    AI_RATE_LIMIT_INTERVIEW: int = 120

    # -----------------------------------------------------------------------
    # Telemetry
    # -----------------------------------------------------------------------

    # Whether to persist AI request logs to the database
    AI_LOG_REQUESTS: bool = True

    # Whether to log raw prompt content (disabled by default for privacy)
    AI_LOG_RAW_PROMPTS: bool = False


settings = AISettings()

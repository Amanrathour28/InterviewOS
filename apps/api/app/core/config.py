from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General
    APP_NAME: str = "InterviewOS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-32-chars-interviewos-platform-security"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            import json
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except Exception:
                    return [v]
            return v
        raise ValueError(v)

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "interviewos"
    POSTGRES_PASSWORD: str = "interviewos_secret"
    POSTGRES_DB: str = "interviewos_db"
    DATABASE_URL: str = (
        "postgresql+asyncpg://interviewos:interviewos_secret@localhost:5432/interviewos_db"
    )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage (MinIO)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "interviewos-assets"
    MINIO_USE_SSL: bool = False

    # AI Gateway (Phase 12)
    AI_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    AI_FALLBACK_PROVIDER: str = "ollama"
    AI_SERVICE_URL: str = "http://localhost:8001/api/v1"
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 3
    AI_TEMPERATURE: float = 0.3
    AI_MAX_TOKENS: int = 2048
    AI_LOG_REQUESTS: bool = True
    AI_STRUCTURED_OUTPUT_MODE: str = "json_schema"

    # Realtime & WebRTC Gateway
    REALTIME_URL: str = "http://localhost:4000"
    STUN_SERVER_URL: str = "stun:stun.l.google.com:19302"
    TURN_SERVER_URL: str = ""
    TURN_USERNAME: str = ""
    TURN_CREDENTIAL: str = ""


settings = Settings()

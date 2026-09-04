"""
Groq Provider Implementation.

Primary remote AI provider using Groq's free-tier API.
Groq supports llama-3.3-70b-versatile and llama-3.1-8b-instant.

Error mapping:
    httpx.TimeoutException       → AIRequestTimeout (retryable)
    httpx.ConnectError           → AIProviderUnavailable (retryable)
    HTTP 429                     → AIProviderRateLimited (retryable)
    HTTP 401 / 403               → AIAuthenticationError (non-retryable)
    HTTP 400                     → AIInvalidRequest (non-retryable)
    HTTP 413                     → AIContextTooLarge (non-retryable)
    HTTP 5xx                     → AIProviderUnavailable (retryable)
    JSON decode error            → AIInvalidResponse (non-retryable)
"""

import json
import logging
import time
from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.gateway.errors import (
    AIAuthenticationError,
    AIContextTooLarge,
    AIInvalidModel,
    AIInvalidRequest,
    AIInvalidResponse,
    AIProviderRateLimited,
    AIProviderUnavailable,
    AIRequestTimeout,
    AISchemaValidationError,
)
from app.gateway.request import AIMessage, AIRequest, AIResponse, AIUsage

logger = logging.getLogger("interviewos.ai.groq")

GROQ_API_BASE = "https://api.groq.com/openai/v1"


class GroqProvider:
    """
    Groq provider using their OpenAI-compatible REST API.
    Does NOT use the Groq Python SDK to avoid an additional mandatory dependency.
    Uses httpx for direct HTTP calls with proper timeout control.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = 30,
    ):
        self._api_key = api_key or settings.GROQ_API_KEY
        self._model = model or settings.GROQ_MODEL
        self._timeout = timeout_seconds or settings.AI_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "groq"

    def _build_headers(self) -> Dict[str, str]:
        if not self._api_key:
            raise AIConfigurationError("GROQ_API_KEY is not configured", provider="groq")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(self, request: AIRequest) -> list:
        messages = [{"role": "system", "content": request.system_prompt}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def _map_error(self, exc: Exception, status_code: Optional[int] = None) -> Exception:
        """Map httpx/HTTP errors to normalized AIError types."""
        if isinstance(exc, httpx.TimeoutException):
            return AIRequestTimeout(provider="groq")
        if isinstance(exc, (httpx.ConnectError, httpx.RemoteProtocolError)):
            return AIProviderUnavailable(provider="groq")
        if status_code is not None:
            if status_code == 401:
                return AIAuthenticationError(provider="groq")
            if status_code == 403:
                return AIAuthenticationError("Groq API key lacks permissions", provider="groq")
            if status_code == 429:
                return AIProviderRateLimited(provider="groq")
            if status_code == 400:
                return AIInvalidRequest(str(exc), provider="groq")
            if status_code == 413:
                return AIContextTooLarge(provider="groq")
            if status_code == 404:
                return AIInvalidModel(str(exc), provider="groq")
            if status_code >= 500:
                return AIProviderUnavailable(f"Groq server error {status_code}", provider="groq")
        return AIProviderUnavailable(str(exc), provider="groq")

    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate a text completion via Groq's OpenAI-compatible endpoint."""
        model = request.model or self._model
        start = time.monotonic()

        payload = {
            "model": model,
            "messages": self._build_messages(request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{GROQ_API_BASE}/chat/completions",
                    headers=self._build_headers(),
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            raise self._map_error(exc) from exc
        except Exception as exc:
            raise AIProviderUnavailable(str(exc), provider="groq") from exc

        latency_ms = int((time.monotonic() - start) * 1000)

        if response.status_code != 200:
            raise self._map_error(Exception(response.text), response.status_code)

        try:
            data = response.json()
        except Exception as exc:
            raise AIInvalidResponse(f"Groq response JSON parse failed: {exc}", provider="groq") from exc

        try:
            content = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason")
            usage_data = data.get("usage", {})
        except (KeyError, IndexError) as exc:
            raise AIInvalidResponse(f"Groq response structure unexpected: {exc}", provider="groq") from exc

        usage = AIUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        logger.debug(
            "Groq generate: model=%s tokens=%d latency=%dms",
            model, usage.total_tokens, latency_ms,
        )

        return AIResponse(
            request_id=request.request_id,
            provider="groq",
            model=model,
            content=content,
            usage=usage,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            metadata=request.metadata,
        )

    async def generate_structured(
        self,
        request: AIRequest,
        schema: Type[BaseModel],
    ) -> AIResponse:
        """
        Generate a structured response validated against a Pydantic schema.
        Uses JSON mode with explicit schema instructions in the system prompt.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)

        # Augment system prompt with JSON schema instruction
        augmented_system = (
            f"{request.system_prompt}\n\n"
            f"IMPORTANT: You must respond with valid JSON that exactly matches this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Respond ONLY with the JSON object. Do not include markdown, explanation, or extra text."
        )

        augmented_request = request.model_copy(
            update={"system_prompt": augmented_system}
        )

        # Use JSON mode in the API payload
        model = request.model or self._model
        start = time.monotonic()

        payload = {
            "model": model,
            "messages": self._build_messages(augmented_request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{GROQ_API_BASE}/chat/completions",
                    headers=self._build_headers(),
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            raise self._map_error(exc) from exc
        except Exception as exc:
            raise AIProviderUnavailable(str(exc), provider="groq") from exc

        latency_ms = int((time.monotonic() - start) * 1000)

        if response.status_code != 200:
            raise self._map_error(Exception(response.text), response.status_code)

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason")
            usage_data = data.get("usage", {})
        except (KeyError, IndexError, Exception) as exc:
            raise AIInvalidResponse(str(exc), provider="groq") from exc

        usage = AIUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        # Validate structured output against schema
        try:
            parsed_json = json.loads(content)
            structured = schema.model_validate(parsed_json)
        except json.JSONDecodeError as exc:
            raise AISchemaValidationError(
                f"Model response is not valid JSON: {exc}",
                provider="groq",
                raw_output=content,
            ) from exc
        except ValidationError as exc:
            raise AISchemaValidationError(
                "Model response does not match expected schema",
                provider="groq",
                raw_output=content,
                validation_errors=exc.errors(),
            ) from exc

        logger.debug(
            "Groq structured: model=%s schema=%s tokens=%d latency=%dms",
            model, schema.__name__, usage.total_tokens, latency_ms,
        )

        return AIResponse(
            request_id=request.request_id,
            provider="groq",
            model=model,
            content=content,
            structured_output=structured,
            usage=usage,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            metadata=request.metadata,
        )

    async def health_check(self) -> bool:
        """Ping Groq API — returns True if reachable and API key is valid."""
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{GROQ_API_BASE}/models",
                    headers=self._build_headers(),
                )
                return response.status_code == 200
        except Exception:
            return False


# Fix forward reference to AIConfigurationError
from app.gateway.errors import AIConfigurationError  # noqa: E402 — circular-safe import at bottom

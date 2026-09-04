"""
Ollama Provider Implementation.

Local fallback provider using Ollama's OpenAI-compatible REST API.
Runs entirely on local hardware — zero API cost, zero external dependency.

Ollama must be running at OLLAMA_BASE_URL (default: http://localhost:11434).
Model must be pulled: `ollama pull llama3.2`

Uses the same AIProvider interface as GroqProvider —
agents cannot tell which provider is active.
"""

import json
import logging
import time
from typing import Type

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.gateway.errors import (
    AIInvalidResponse,
    AIProviderUnavailable,
    AIRequestTimeout,
    AISchemaValidationError,
)
from app.gateway.request import AIRequest, AIResponse, AIUsage

logger = logging.getLogger("interviewos.ai.ollama")


class OllamaProvider:
    """
    Ollama local provider using Ollama's OpenAI-compatible endpoint.
    Implements the same AIProvider interface as GroqProvider.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ):
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or settings.OLLAMA_MODEL
        # Ollama is slower (local inference) — allow more time
        self._timeout = timeout_seconds or max(settings.AI_TIMEOUT_SECONDS * 2, 60)

    @property
    def provider_name(self) -> str:
        return "ollama"

    def _build_messages(self, request: AIRequest) -> list:
        messages = [{"role": "system", "content": request.system_prompt}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def _map_error(self, exc: Exception) -> Exception:
        if isinstance(exc, httpx.TimeoutException):
            return AIRequestTimeout(provider="ollama")
        if isinstance(exc, (httpx.ConnectError, httpx.RemoteProtocolError)):
            return AIProviderUnavailable(
                "Ollama is not running or unreachable at configured URL", provider="ollama"
            )
        return AIProviderUnavailable(str(exc), provider="ollama")

    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate text via Ollama's OpenAI-compatible /chat/completions endpoint."""
        model = request.model or self._model
        start = time.monotonic()

        payload = {
            "model": model,
            "messages": self._build_messages(request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            raise self._map_error(exc) from exc
        except Exception as exc:
            raise AIProviderUnavailable(str(exc), provider="ollama") from exc

        latency_ms = int((time.monotonic() - start) * 1000)

        if response.status_code != 200:
            raise AIProviderUnavailable(
                f"Ollama returned HTTP {response.status_code}: {response.text[:200]}",
                provider="ollama",
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason")
            usage_data = data.get("usage", {})
        except (KeyError, IndexError, Exception) as exc:
            raise AIInvalidResponse(str(exc), provider="ollama") from exc

        usage = AIUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        logger.debug("Ollama generate: model=%s latency=%dms", model, latency_ms)

        return AIResponse(
            request_id=request.request_id,
            provider="ollama",
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
        Generate structured output from Ollama.
        Uses explicit JSON schema instruction in system prompt + format=json.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)

        augmented_system = (
            f"{request.system_prompt}\n\n"
            f"IMPORTANT: You must respond with valid JSON that exactly matches this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Respond ONLY with the JSON object. No markdown, no explanation, no extra text."
        )

        model = request.model or self._model
        start = time.monotonic()

        messages = [{"role": "system", "content": augmented_system}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
            "format": "json",  # Ollama native JSON mode
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            raise self._map_error(exc) from exc
        except Exception as exc:
            raise AIProviderUnavailable(str(exc), provider="ollama") from exc

        latency_ms = int((time.monotonic() - start) * 1000)

        if response.status_code != 200:
            raise AIProviderUnavailable(
                f"Ollama returned HTTP {response.status_code}: {response.text[:200]}",
                provider="ollama",
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason")
            usage_data = data.get("usage", {})
        except (KeyError, IndexError, Exception) as exc:
            raise AIInvalidResponse(str(exc), provider="ollama") from exc

        usage = AIUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        # Validate structured output
        try:
            parsed_json = json.loads(content)
            structured = schema.model_validate(parsed_json)
        except json.JSONDecodeError as exc:
            raise AISchemaValidationError(
                f"Ollama response is not valid JSON: {exc}",
                provider="ollama",
                raw_output=content,
            ) from exc
        except ValidationError as exc:
            raise AISchemaValidationError(
                "Ollama response does not match expected schema",
                provider="ollama",
                raw_output=content,
                validation_errors=exc.errors(),
            ) from exc

        logger.debug("Ollama structured: model=%s schema=%s latency=%dms", model, schema.__name__, latency_ms)

        return AIResponse(
            request_id=request.request_id,
            provider="ollama",
            model=model,
            content=content,
            structured_output=structured,
            usage=usage,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            metadata=request.metadata,
        )

    async def health_check(self) -> bool:
        """Ping Ollama API endpoint — returns True if reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

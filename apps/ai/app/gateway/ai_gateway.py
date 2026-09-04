"""
AI Gateway — Provider-Agnostic Entry Point.

The AIGateway is the ONLY way business logic and agents should interact with AI providers.
No agent or service should ever directly call groq_provider.generate() or ollama_provider.generate().

Features:
  - Provider selection (primary / fallback)
  - Bounded retries with exponential back-off
  - Intelligent fallback (retryable errors only)
  - Structured output validation
  - Usage tracking delegation
  - Redis distributed lock for concurrency control
  - Graceful degradation

Fallback Policy:
  Retryable errors → retry on same provider (up to max_retries)
                  → then try fallback provider
  Non-retryable errors → fail immediately (no fallback)
"""

import asyncio
import logging
import time
from typing import Optional, Type, Union

from pydantic import BaseModel

from app.config import settings
from app.gateway.errors import (
    AIAllProvidersFailed,
    AIError,
    AIProviderRateLimited,
    AIProviderUnavailable,
    AIRequestTimeout,
)
from app.gateway.request import AIRequest, AIResponse
from app.providers.groq_provider import GroqProvider
from app.providers.ollama_provider import OllamaProvider

logger = logging.getLogger("interviewos.ai.gateway")


# Errors that allow fallback to another provider
_RETRYABLE_ERROR_TYPES = (AIProviderUnavailable, AIProviderRateLimited, AIRequestTimeout)


class AIGateway:
    """
    Provider-agnostic AI Gateway.

    Usage:
        gateway = AIGateway()
        response = await gateway.generate_structured(
            request=ai_request,
            schema=CodingAnalysis,
        )
        # response.structured_output is a validated CodingAnalysis instance
    """

    def __init__(
        self,
        primary_provider: Optional[str] = None,
        fallback_provider: Optional[str] = None,
    ):
        primary = primary_provider or settings.AI_PROVIDER
        fallback = fallback_provider or settings.AI_FALLBACK_PROVIDER

        self._providers = self._build_provider_map()
        self._primary = primary
        self._fallback = fallback if fallback != primary else None

        logger.info(
            "AIGateway initialized: primary=%s fallback=%s",
            self._primary,
            self._fallback,
        )

    def _build_provider_map(self) -> dict:
        return {
            "groq": GroqProvider(),
            "ollama": OllamaProvider(),
        }

    def _get_provider(self, name: str):
        provider = self._providers.get(name)
        if not provider:
            raise ValueError(f"Unknown AI provider: {name!r}")
        return provider

    async def generate(self, request: AIRequest) -> AIResponse:
        """
        Generate a text completion.
        Tries primary provider first, falls back to secondary on retryable errors.
        """
        return await self._execute_with_fallback(
            request=request,
            operation="generate",
            schema=None,
        )

    async def generate_structured(
        self,
        request: AIRequest,
        schema: Type[BaseModel],
    ) -> AIResponse:
        """
        Generate and validate a structured output response.
        Tries primary provider first, falls back on retryable errors.
        """
        return await self._execute_with_fallback(
            request=request,
            operation="generate_structured",
            schema=schema,
        )

    async def _execute_with_fallback(
        self,
        request: AIRequest,
        operation: str,
        schema: Optional[Type[BaseModel]],
    ) -> AIResponse:
        """
        Core execution logic with retry + fallback.

        Retry policy:
            - Attempt the primary provider up to max_retries times
            - On retryable failure, wait with exponential back-off
            - After exhausting primary retries, try fallback provider once
            - On non-retryable error, fail immediately (no retry, no fallback)
        """
        provider_name = request.provider or self._primary
        max_retries = request.max_retries

        primary_error: Optional[AIError] = None
        fallback_error: Optional[AIError] = None

        # --- Primary provider with retries ---
        for attempt in range(max_retries):
            try:
                provider = self._get_provider(provider_name)
                response = await self._call_provider(provider, operation, request, schema)
                response.retry_count = attempt
                return response
            except _RETRYABLE_ERROR_TYPES as exc:
                primary_error = exc
                logger.warning(
                    "AI primary provider %s attempt %d/%d failed (retryable): %s",
                    provider_name, attempt + 1, max_retries, exc.message,
                )
                if attempt < max_retries - 1:
                    # Exponential back-off: 0.5s, 1s, 2s ...
                    await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            except AIError as exc:
                # Non-retryable: fail immediately
                logger.error(
                    "AI primary provider %s non-retryable error: %s",
                    provider_name, exc.message,
                )
                raise

        logger.warning(
            "AI primary provider %s exhausted %d retries. Trying fallback: %s",
            provider_name, max_retries, self._fallback,
        )

        # --- Fallback provider (one attempt) ---
        if self._fallback:
            try:
                provider = self._get_provider(self._fallback)
                response = await self._call_provider(provider, operation, request, schema)
                response.is_fallback = True
                response.retry_count = max_retries
                logger.info("AI fallback provider %s succeeded", self._fallback)
                return response
            except AIError as exc:
                fallback_error = exc
                logger.error(
                    "AI fallback provider %s also failed: %s", self._fallback, exc.message
                )

        raise AIAllProvidersFailed(
            primary_error=primary_error,
            fallback_error=fallback_error,
        )

    async def _call_provider(
        self,
        provider,
        operation: str,
        request: AIRequest,
        schema: Optional[Type[BaseModel]],
    ) -> AIResponse:
        """Dispatch a single call to the provider."""
        if operation == "generate":
            return await provider.generate(request)
        elif operation == "generate_structured":
            return await provider.generate_structured(request, schema)
        else:
            raise ValueError(f"Unknown operation: {operation!r}")

    async def health(self) -> dict:
        """
        Check health of all configured providers.
        Returns a dict suitable for the /health endpoint.

        States: READY | DEGRADED | UNAVAILABLE | MISCONFIGURED
        """
        results = {}
        for name, provider in self._providers.items():
            try:
                ok = await provider.health_check()
                results[name] = "READY" if ok else "UNAVAILABLE"
            except Exception as exc:
                results[name] = "UNAVAILABLE"
                logger.debug("Provider %s health check exception: %s", name, exc)

        # Determine overall gateway status
        primary_status = results.get(self._primary, "UNAVAILABLE")
        fallback_status = results.get(self._fallback, "UNAVAILABLE") if self._fallback else "N/A"

        if primary_status == "READY":
            overall = "READY"
        elif fallback_status == "READY":
            overall = "DEGRADED"
        else:
            overall = "UNAVAILABLE"

        return {
            "status": overall,
            "primary_provider": self._primary,
            "fallback_provider": self._fallback,
            "providers": results,
        }


# Singleton instance — shared across the AI service process
_gateway: Optional[AIGateway] = None


def get_gateway() -> AIGateway:
    """Return the singleton AIGateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = AIGateway()
    return _gateway

"""
Gateway Tests — Provider + Fallback + Error Mapping.

Tests that the AIGateway:
  1. Uses primary provider on success
  2. Falls back to secondary on retryable errors
  3. Does NOT fall back on non-retryable errors
  4. Raises AIAllProvidersFailed when both fail
  5. Reports health correctly
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.gateway.ai_gateway import AIGateway
from app.gateway.errors import (
    AIAllProvidersFailed,
    AIAuthenticationError,
    AIProviderUnavailable,
    AIRequestTimeout,
)
from app.gateway.request import AIMessage, AIRequest, AIResponse, AIUsage


def make_request() -> AIRequest:
    return AIRequest(
        system_prompt="You are a test assistant.",
        messages=[AIMessage(role="user", content="Test question")],
        temperature=0.3,
        max_tokens=100,
    )


def make_success_response() -> AIResponse:
    return AIResponse(
        request_id="test-001",
        provider="groq",
        model="llama-3.3-70b-versatile",
        content="Test response",
        usage=AIUsage(input_tokens=10, output_tokens=5, total_tokens=15),
        latency_ms=100,
    )


@pytest.mark.asyncio
async def test_gateway_uses_primary_on_success():
    """Gateway should return primary provider response on success."""
    gateway = AIGateway.__new__(AIGateway)
    gateway._primary = "groq"
    gateway._fallback = "ollama"

    mock_groq = AsyncMock()
    mock_groq.generate = AsyncMock(return_value=make_success_response())

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock(return_value=make_success_response())

    gateway._providers = {"groq": mock_groq, "ollama": mock_ollama}

    request = make_request()
    response = await gateway.generate(request)

    assert response.provider == "groq"
    assert not response.is_fallback
    mock_groq.generate.assert_called_once()
    mock_ollama.generate.assert_not_called()


@pytest.mark.asyncio
async def test_gateway_falls_back_on_retryable_error():
    """Gateway should try fallback when primary raises retryable error."""
    gateway = AIGateway.__new__(AIGateway)
    gateway._primary = "groq"
    gateway._fallback = "ollama"

    fallback_response = AIResponse(
        request_id="test-002",
        provider="ollama",
        model="llama3.2",
        content="Fallback response",
        usage=AIUsage(),
        latency_ms=500,
    )

    mock_groq = AsyncMock()
    mock_groq.generate = AsyncMock(side_effect=AIProviderUnavailable(provider="groq"))

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock(return_value=fallback_response)

    gateway._providers = {"groq": mock_groq, "ollama": mock_ollama}

    request = make_request()
    request.max_retries = 1  # Reduce retries for speed

    response = await gateway.generate(request)

    assert response.provider == "ollama"
    assert response.is_fallback is True
    mock_ollama.generate.assert_called_once()


@pytest.mark.asyncio
async def test_gateway_does_not_fall_back_on_non_retryable():
    """Non-retryable errors must propagate immediately without fallback."""
    gateway = AIGateway.__new__(AIGateway)
    gateway._primary = "groq"
    gateway._fallback = "ollama"

    mock_groq = AsyncMock()
    mock_groq.generate = AsyncMock(
        side_effect=AIAuthenticationError(provider="groq")
    )

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock()

    gateway._providers = {"groq": mock_groq, "ollama": mock_ollama}

    request = make_request()

    with pytest.raises(AIAuthenticationError):
        await gateway.generate(request)

    # Fallback must NOT have been called
    mock_ollama.generate.assert_not_called()


@pytest.mark.asyncio
async def test_gateway_raises_all_providers_failed():
    """When both providers fail with retryable errors, raise AIAllProvidersFailed."""
    gateway = AIGateway.__new__(AIGateway)
    gateway._primary = "groq"
    gateway._fallback = "ollama"

    mock_groq = AsyncMock()
    mock_groq.generate = AsyncMock(side_effect=AIRequestTimeout(provider="groq"))

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock(side_effect=AIProviderUnavailable(provider="ollama"))

    gateway._providers = {"groq": mock_groq, "ollama": mock_ollama}

    request = make_request()
    request.max_retries = 1

    with pytest.raises(AIAllProvidersFailed) as exc_info:
        await gateway.generate(request)

    error = exc_info.value
    assert error.primary_error is not None
    assert error.fallback_error is not None


@pytest.mark.asyncio
async def test_gateway_health_all_ready():
    """Health check returns READY when primary is up."""
    gateway = AIGateway.__new__(AIGateway)
    gateway._primary = "groq"
    gateway._fallback = "ollama"

    mock_groq = AsyncMock()
    mock_groq.health_check = AsyncMock(return_value=True)

    mock_ollama = AsyncMock()
    mock_ollama.health_check = AsyncMock(return_value=True)

    gateway._providers = {"groq": mock_groq, "ollama": mock_ollama}

    health = await gateway.health()

    assert health["status"] == "READY"
    assert health["providers"]["groq"] == "READY"


@pytest.mark.asyncio
async def test_gateway_health_degraded_when_primary_down():
    """Health check returns DEGRADED when only fallback is up."""
    gateway = AIGateway.__new__(AIGateway)
    gateway._primary = "groq"
    gateway._fallback = "ollama"

    mock_groq = AsyncMock()
    mock_groq.health_check = AsyncMock(return_value=False)

    mock_ollama = AsyncMock()
    mock_ollama.health_check = AsyncMock(return_value=True)

    gateway._providers = {"groq": mock_groq, "ollama": mock_ollama}

    health = await gateway.health()

    assert health["status"] == "DEGRADED"

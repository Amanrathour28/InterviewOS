"""
Normalized AI Error Hierarchy.

Agents and business logic depend only on these error types —
never on Groq-specific or Ollama-specific exception classes.
This allows transparent provider switching without changing agent code.
"""

from typing import Optional


class AIError(Exception):
    """Base class for all InterviewOS AI errors."""

    def __init__(self, message: str, provider: Optional[str] = None, retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.message = message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider!r}, message={self.message!r})"


# ---------------------------------------------------------------------------
# Provider-Level Errors (retryable — infrastructure/transient issues)
# ---------------------------------------------------------------------------

class AIProviderUnavailable(AIError):
    """Provider endpoint is unreachable or returned a 503/502."""

    def __init__(self, message: str = "AI provider is unavailable", provider: Optional[str] = None):
        super().__init__(message, provider=provider, retryable=True)


class AIProviderRateLimited(AIError):
    """Provider returned 429 Too Many Requests."""

    def __init__(
        self,
        message: str = "AI provider rate limit exceeded",
        provider: Optional[str] = None,
        retry_after_seconds: Optional[int] = None,
    ):
        super().__init__(message, provider=provider, retryable=True)
        self.retry_after_seconds = retry_after_seconds


class AIRequestTimeout(AIError):
    """Provider did not respond within the configured timeout."""

    def __init__(self, message: str = "AI request timed out", provider: Optional[str] = None):
        super().__init__(message, provider=provider, retryable=True)


# ---------------------------------------------------------------------------
# Request-Level Errors (non-retryable — invalid input or config)
# ---------------------------------------------------------------------------

class AIAuthenticationError(AIError):
    """API key is missing, invalid, or expired. Non-retryable."""

    def __init__(self, message: str = "AI provider authentication failed", provider: Optional[str] = None):
        super().__init__(message, provider=provider, retryable=False)


class AIInvalidRequest(AIError):
    """The request was malformed or contains unsupported parameters. Non-retryable."""

    def __init__(self, message: str = "Invalid AI request", provider: Optional[str] = None):
        super().__init__(message, provider=provider, retryable=False)


class AIContextTooLarge(AIError):
    """The combined prompt exceeds the model's context window. Non-retryable."""

    def __init__(self, message: str = "Prompt exceeds model context window", provider: Optional[str] = None):
        super().__init__(message, provider=provider, retryable=False)


class AIInvalidModel(AIError):
    """The requested model does not exist or is not supported. Non-retryable."""

    def __init__(self, message: str = "Invalid or unsupported AI model", provider: Optional[str] = None):
        super().__init__(message, provider=provider, retryable=False)


class AIConfigurationError(AIError):
    """The AI service is misconfigured (missing API key, bad URL, etc.). Non-retryable."""

    def __init__(self, message: str = "AI service misconfigured", provider: Optional[str] = None):
        super().__init__(message, provider=provider, retryable=False)


# ---------------------------------------------------------------------------
# Output / Validation Errors (non-retryable by default)
# ---------------------------------------------------------------------------

class AIInvalidResponse(AIError):
    """Model returned a response that could not be parsed. Non-retryable."""

    def __init__(self, message: str = "AI returned an unparseable response", provider: Optional[str] = None):
        super().__init__(message, provider=provider, retryable=False)


class AISchemaValidationError(AIError):
    """
    Model output did not conform to the expected structured output schema.
    May trigger a bounded repair attempt before failing.
    """

    def __init__(
        self,
        message: str = "AI output failed schema validation",
        provider: Optional[str] = None,
        raw_output: Optional[str] = None,
        validation_errors: Optional[list] = None,
    ):
        super().__init__(message, provider=provider, retryable=False)
        self.raw_output = raw_output
        self.validation_errors = validation_errors or []


class AIAllProvidersFailed(AIError):
    """
    All configured providers (primary + fallback) have failed.
    InterviewOS must degrade gracefully and continue without AI.
    """

    def __init__(
        self,
        message: str = "All AI providers failed",
        primary_error: Optional[AIError] = None,
        fallback_error: Optional[AIError] = None,
    ):
        super().__init__(message, retryable=False)
        self.primary_error = primary_error
        self.fallback_error = fallback_error


# ---------------------------------------------------------------------------
# Security / Tenant Errors
# ---------------------------------------------------------------------------

class AITenantIsolationError(AIError):
    """
    A request attempted to access context from a different workspace/session.
    This should never occur in production — it indicates a programming error.
    """

    def __init__(self, message: str = "AI tenant isolation violation"):
        super().__init__(message, retryable=False)


class AIUnauthorizedError(AIError):
    """The caller does not have permission to invoke this AI capability."""

    def __init__(self, message: str = "Unauthorized AI request"):
        super().__init__(message, retryable=False)

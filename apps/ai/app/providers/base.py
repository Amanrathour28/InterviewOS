"""
AIProvider Protocol.

Every provider (Groq, Ollama, future providers) must implement this interface.
Agents never import provider-specific classes — they depend only on this protocol.
"""

from typing import Optional, Protocol, runtime_checkable, Type
from pydantic import BaseModel

from app.gateway.request import AIRequest, AIResponse


@runtime_checkable
class AIProvider(Protocol):
    """
    Protocol defining the contract every AI provider must satisfy.
    Runtime-checkable so we can assert compliance in tests.
    """

    @property
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g. 'groq', 'ollama')."""
        ...

    async def generate(self, request: AIRequest) -> AIResponse:
        """
        Generate a text completion.

        Raises:
            AIProviderUnavailable: Provider endpoint unreachable.
            AIProviderRateLimited: Provider 429.
            AIRequestTimeout: No response within timeout.
            AIAuthenticationError: Invalid API key.
            AIInvalidRequest: Malformed request payload.
            AIContextTooLarge: Prompt exceeds context window.
            AIInvalidModel: Unknown/unsupported model.
            AIInvalidResponse: Response could not be parsed.
        """
        ...

    async def generate_structured(
        self,
        request: AIRequest,
        schema: Type[BaseModel],
    ) -> AIResponse:
        """
        Generate a response that validates against the provided Pydantic schema.

        The provider should:
        1. Instruct the model to emit JSON conforming to schema.
        2. Parse and validate the response.
        3. Raise AISchemaValidationError if validation fails.

        The structured_output field of AIResponse will be populated with
        the validated Pydantic model instance.
        """
        ...

    async def health_check(self) -> bool:
        """
        Returns True if the provider endpoint is reachable and usable.
        Must not raise — return False on any failure.
        """
        ...

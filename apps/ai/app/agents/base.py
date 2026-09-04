"""
Base Agent Contract.

All InterviewOS AI agents must implement this interface.
The contract defines:
  - AgentContext: what an agent receives as input
  - AgentResult: what an agent must produce as output
  - BaseAgent: abstract base class with shared utility methods

Agents are specialized reasoning units. They do not:
  - Directly query the database
  - Call provider APIs directly
  - Modify interview state
  - Send realtime events directly

They receive an AgentContext, call the AIGateway, and return an AgentResult.
All state mutation and event dispatch is handled by the application layer.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel

from app.context.builder import InterviewContext
from app.gateway.ai_gateway import AIGateway, get_gateway
from app.gateway.errors import AIError
from app.gateway.request import AIMessage, AIRequest, AIResponse
from app.telemetry import usage_tracker

logger = logging.getLogger("interviewos.ai.agents")


@dataclass
class AgentContext:
    """
    Input context for every agent invocation.
    Contains authorization boundaries that must be honored.
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Tenant isolation — must be validated before processing
    workspace_id: str = ""
    interview_id: str = ""
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    # Interview state
    current_stage: Optional[str] = None

    # Caller permissions
    is_interviewer: bool = False

    # Structured interview context (already filtered + budgeted)
    context: Optional[InterviewContext] = None

    # Task-specific additional data
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """
    Output from every agent invocation.
    Always structured — never raw text.
    """

    # Agent identity
    agent_name: str
    request_id: str

    # Execution status
    status: Literal["success", "failed", "degraded"]

    # Structured output (the Pydantic model instance)
    output: Optional[Any] = None

    # Confidence from 0.0 to 1.0
    confidence: float = 0.0

    # Evidence references (must be grounded in actual interview data)
    evidence: List[str] = field(default_factory=list)

    # Error info (populated when status != "success")
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Observability
    provider: Optional[str] = None
    model: Optional[str] = None
    is_fallback: bool = False
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseAgent(ABC):
    """
    Abstract base class for all InterviewOS AI agents.

    Subclasses must implement:
      - agent_name: str property
      - run(): the agent's core logic

    Subclasses should use:
      - self.gateway: AIGateway for all LLM calls
      - self._make_request(): to build typed AIRequests
      - self._log(): to persist telemetry
    """

    AGENT_VERSION = "1.0"

    def __init__(self, gateway: Optional[AIGateway] = None):
        self.gateway = gateway or get_gateway()
        self._logger = logging.getLogger(f"interviewos.ai.agents.{self.agent_name}")

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Unique agent identifier."""
        ...

    @abstractmethod
    async def run(self, ctx: AgentContext) -> AgentResult:
        """Execute the agent and return a structured result."""
        ...

    def _make_request(
        self,
        ctx: AgentContext,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        prompt_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> AIRequest:
        """Build a typed AIRequest from agent context."""
        return AIRequest(
            request_id=ctx.request_id,
            model=model,
            system_prompt=system_prompt,
            messages=[AIMessage(role="user", content=user_message)],
            temperature=temperature,
            max_tokens=max_tokens,
            workspace_id=ctx.workspace_id,
            interview_id=ctx.interview_id,
            session_id=ctx.session_id,
            user_id=ctx.user_id,
            agent_name=self.agent_name,
            task_type=task_type or self.agent_name,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            metadata={
                "agent_version": self.AGENT_VERSION,
                "current_stage": ctx.current_stage,
            },
        )

    async def _log_result(
        self,
        ctx: AgentContext,
        result: AgentResult,
        prompt_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
    ) -> None:
        """Persist telemetry for this agent invocation."""
        await usage_tracker.log_request(
            request_id=result.request_id,
            workspace_id=ctx.workspace_id,
            interview_id=ctx.interview_id,
            user_id=ctx.user_id,
            agent_name=result.agent_name,
            provider=result.provider or "unknown",
            model=result.model or "unknown",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.input_tokens + result.output_tokens,
            latency_ms=result.latency_ms,
            success=result.status == "success",
            error_type=result.error_type,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            task_type=self.agent_name,
            is_fallback=result.is_fallback,
        )

    def _build_success_result(
        self,
        ctx: AgentContext,
        output: Any,
        response: AIResponse,
        confidence: float = 0.8,
        evidence: Optional[List[str]] = None,
    ) -> AgentResult:
        """Construct a successful AgentResult from an AIResponse."""
        return AgentResult(
            agent_name=self.agent_name,
            request_id=ctx.request_id,
            status="success",
            output=output,
            confidence=confidence,
            evidence=evidence or [],
            provider=response.provider,
            model=response.model,
            is_fallback=response.is_fallback,
            latency_ms=response.latency_ms,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def _build_error_result(
        self,
        ctx: AgentContext,
        error: Exception,
    ) -> AgentResult:
        """Construct a failed AgentResult from an exception."""
        error_type = type(error).__name__
        error_message = str(error)
        self._logger.warning("Agent %s failed: %s: %s", self.agent_name, error_type, error_message)
        return AgentResult(
            agent_name=self.agent_name,
            request_id=ctx.request_id,
            status="failed",
            error_type=error_type,
            error_message=error_message,
        )

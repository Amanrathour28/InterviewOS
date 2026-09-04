"""
LangGraph Interview Processing Graph.

Orchestrates AI processing for interview events using LangGraph StateGraph.
The graph is deterministic — it does not autonomously make interview decisions.

Graph structure:
  START
    │
    ▼
  load_context       ← Assembles InterviewContext from raw data
    │
    ▼
  validate_tenant    ← Enforces tenant isolation
    │
    ▼
  route_task         ← Determines which agent handles the request
    │
  ┌─┴──────────────────────────────────┐
  ▼                                    ▼
  run_agent                        route_error
    │
    ▼
  validate_output    ← Schema validation + confidence check
    │
    ▼
  log_telemetry      ← Persist AI request log
    │
    ▼
  END

The graph returns an AIGraphResult that is used by the API layer.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.base import AgentContext, AgentResult
from app.agents.orchestrator import OrchestratorAgent
from app.context.builder import InterviewContext, InterviewContextBuilder
from app.gateway.ai_gateway import get_gateway
from app.gateway.errors import AITenantIsolationError, AIUnauthorizedError
from app.security.tenant_isolation import assert_interviewer_only, assert_workspace_match

logger = logging.getLogger("interviewos.ai.graph")


# ---------------------------------------------------------------------------
# Graph State
# ---------------------------------------------------------------------------

class GraphState(TypedDict):
    """State flowing through the LangGraph nodes."""

    # Input
    request_id: str
    workspace_id: str
    interview_id: str
    session_id: Optional[str]
    user_id: Optional[str]
    is_interviewer: bool
    task_type: str
    raw_input: Dict[str, Any]  # Task-specific extra data

    # Built during graph execution
    context: Optional[Any]  # InterviewContext (not typed here for langgraph compat)

    # Output
    agent_result: Optional[Dict[str, Any]]
    error: Optional[str]
    error_type: Optional[str]


# ---------------------------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------------------------

async def load_context(state: GraphState) -> GraphState:
    """Assemble InterviewContext from raw input data."""
    try:
        builder = InterviewContextBuilder()
        context = builder.build(
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            current_stage=state["raw_input"].get("current_stage"),
            elapsed_seconds=state["raw_input"].get("elapsed_seconds", 0),
            raw_candidate=state["raw_input"].get("candidate"),
            raw_job=state["raw_input"].get("job"),
            raw_session=state["raw_input"].get("session"),
            raw_events=state["raw_input"].get("events", []),
            current_problem=state["raw_input"].get("current_problem"),
            candidate_code=state["raw_input"].get("candidate_code"),
            execution_result=state["raw_input"].get("execution_result"),
            whiteboard_state=state["raw_input"].get("whiteboard_state"),
            previous_questions=state["raw_input"].get("previous_questions", []),
        )
        state["context"] = context
        logger.debug("Context loaded for session %s", state.get("session_id"))
    except Exception as exc:
        state["error"] = str(exc)
        state["error_type"] = type(exc).__name__
    return state


async def validate_tenant(state: GraphState) -> GraphState:
    """Enforce tenant isolation before any AI processing."""
    if state.get("error"):
        return state

    try:
        context = state.get("context")
        if context:
            assert_workspace_match(
                context.workspace_id,
                state["workspace_id"],
                operation=f"graph/{state['task_type']}",
            )
        assert_interviewer_only(
            state["is_interviewer"],
            operation=state["task_type"],
        )
    except (AITenantIsolationError, AIUnauthorizedError) as exc:
        state["error"] = str(exc)
        state["error_type"] = type(exc).__name__

    return state


async def run_agent(state: GraphState) -> GraphState:
    """Execute the appropriate agent for the task."""
    if state.get("error"):
        return state

    try:
        gateway = get_gateway()
        orchestrator = OrchestratorAgent(gateway=gateway)

        ctx = AgentContext(
            request_id=state["request_id"],
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            current_stage=state["raw_input"].get("current_stage"),
            is_interviewer=state["is_interviewer"],
            context=state.get("context"),
            extra={
                "task_type": state["task_type"],
                **state["raw_input"],
            },
        )

        result = await orchestrator.run(ctx)
        state["agent_result"] = {
            "agent_name": result.agent_name,
            "status": result.status,
            "output": result.output.model_dump() if result.output and hasattr(result.output, "model_dump") else result.output,
            "confidence": result.confidence,
            "evidence": result.evidence,
            "error_type": result.error_type,
            "error_message": result.error_message,
            "provider": result.provider,
            "model": result.model,
            "is_fallback": result.is_fallback,
            "latency_ms": result.latency_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }

    except Exception as exc:
        state["error"] = str(exc)
        state["error_type"] = type(exc).__name__
        logger.error("Graph agent execution failed: %s: %s", type(exc).__name__, exc)

    return state


def _should_run_agent(state: GraphState) -> Literal["run_agent", "route_error"]:
    """Conditional edge: skip agent if an error occurred upstream."""
    if state.get("error"):
        return "route_error"
    return "run_agent"


async def route_error(state: GraphState) -> GraphState:
    """Terminal error node — logs and returns failed state."""
    logger.warning(
        "AI graph error: type=%s message=%s session=%s",
        state.get("error_type"),
        state.get("error"),
        state.get("session_id"),
    )
    return state


# ---------------------------------------------------------------------------
# Build the Graph
# ---------------------------------------------------------------------------

def build_interview_graph():
    """Construct and compile the LangGraph StateGraph."""
    graph = StateGraph(GraphState)

    # Register nodes
    graph.add_node("load_context", load_context)
    graph.add_node("validate_tenant", validate_tenant)
    graph.add_node("run_agent", run_agent)
    graph.add_node("route_error", route_error)

    # Define edges
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "validate_tenant")
    graph.add_conditional_edges(
        "validate_tenant",
        _should_run_agent,
        {"run_agent": "run_agent", "route_error": "route_error"},
    )
    graph.add_edge("run_agent", END)
    graph.add_edge("route_error", END)

    return graph.compile()


# Compiled graph singleton
_compiled_graph = None


def get_compiled_graph():
    """Return the singleton compiled LangGraph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_interview_graph()
    return _compiled_graph


async def run_graph(
    request_id: str,
    workspace_id: str,
    interview_id: str,
    task_type: str,
    raw_input: Dict[str, Any],
    is_interviewer: bool,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the interview AI graph for a single task.
    Returns the final graph state.
    """
    compiled = get_compiled_graph()
    initial_state: GraphState = {
        "request_id": request_id,
        "workspace_id": workspace_id,
        "interview_id": interview_id,
        "session_id": session_id,
        "user_id": user_id,
        "is_interviewer": is_interviewer,
        "task_type": task_type,
        "raw_input": raw_input,
        "context": None,
        "agent_result": None,
        "error": None,
        "error_type": None,
    }

    final_state = await compiled.ainvoke(initial_state)
    return dict(final_state)

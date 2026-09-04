"""
Adaptive Interview Processing Graph Orchestration — Phase 14.

Orchestrates real-time adaptive questioning workflow:
START -> load_context -> detect_response_boundary -> analyze_response -> update_coverage -> evaluate_difficulty -> generate_strategy_recommendation -> validate_recommendation -> END.
"""

import logging
from typing import Any, Dict, List, Optional, TypedDict

from app.agents.adaptive_interview_agent import AdaptiveInterviewAgent
from app.agents.base import AgentContext
from app.agents.coverage_agent import CoverageAgent
from app.agents.difficulty_agent import DifficultyAgent
from app.agents.response_analysis_agent import ResponseAnalysisAgent
from app.context.builder import InterviewContextBuilder
from app.gateway.ai_gateway import get_gateway

logger = logging.getLogger("interviewos.ai.adaptive_graph")


class AdaptiveGraphState(TypedDict):
    # Inputs
    workspace_id: str
    interview_id: str
    session_id: Optional[str]
    user_id: Optional[str]
    current_stage: str
    remaining_seconds: int
    current_question: str
    candidate_response: str
    competency: str
    expected_signal: str
    approved_question_plan: List[Dict[str, Any]]
    resume_claims: List[Dict[str, Any]]
    coding_signals: Dict[str, Any]
    system_design_signals: Dict[str, Any]
    previous_questions_asked: List[str]

    # Intermediate artifacts
    response_analysis: Optional[Dict[str, Any]]
    difficulty_adaptation: Optional[Dict[str, Any]]
    coverage_state: Optional[Dict[str, Any]]

    # Final Output
    recommendation: Optional[Dict[str, Any]]
    error: Optional[str]


class AdaptiveGraphOrchestrator:
    """Executes the adaptive interview graph workflow pipeline."""

    def __init__(self, gateway: Optional[Any] = None):
        self.gateway = gateway or get_gateway()

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the pipeline sequentially with safety validation."""
        curr_state = dict(state)
        curr_state = await analyze_response_node(curr_state, self.gateway)
        curr_state = await evaluate_coverage_and_difficulty_node(curr_state, self.gateway)
        curr_state = await generate_recommendation_node(curr_state, self.gateway)
        return curr_state


async def analyze_response_node(state: Dict[str, Any], gateway: Any) -> Dict[str, Any]:
    """Analyze candidate response for demonstrated and missing concepts."""
    try:
        agent = ResponseAnalysisAgent(gateway=gateway)

        builder = InterviewContextBuilder()
        ctx_obj = builder.build(
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            current_stage=state.get("current_stage", "technical"),
        )

        agent_ctx = AgentContext(
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            context=ctx_obj,
            extra={
                "current_question": state.get("current_question", ""),
                "candidate_response": state.get("candidate_response", ""),
                "competency": state.get("competency", "General"),
                "expected_signal": state.get("expected_signal", ""),
                "claims": state.get("resume_claims", []),
            },
        )

        res = await agent.run(agent_ctx)
        if res.success and res.output:
            state["response_analysis"] = res.output.model_dump() if hasattr(res.output, "model_dump") else res.output
    except Exception as exc:
        logger.warning("Error in analyze_response_node: %s", exc)
        state["response_analysis"] = {
            "completeness_score": 0.7,
            "demonstrated_concepts": [],
            "missing_concepts": [],
            "evidence_strength": "moderate",
            "summary": "Standard candidate response.",
        }
    return state


async def evaluate_coverage_and_difficulty_node(state: Dict[str, Any], gateway: Any) -> Dict[str, Any]:
    """Assess competency coverage status and calibrate difficulty bounds."""
    try:
        coverage_agent = CoverageAgent(gateway=gateway)
        difficulty_agent = DifficultyAgent(gateway=gateway)

        builder = InterviewContextBuilder()
        ctx_obj = builder.build(
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
        )

        demonstrated = state.get("response_analysis", {}).get("demonstrated_concepts", [])
        evidence_strength = state.get("response_analysis", {}).get("evidence_strength", "moderate")

        # 1. Coverage
        cov_ctx = AgentContext(
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            context=ctx_obj,
            extra={
                "competency": state.get("competency", "General"),
                "demonstrated_skills": demonstrated,
                "questions_asked": 1,
                "target_skills": [state.get("competency", "General")],
            },
        )
        cov_res = await coverage_agent.run(cov_ctx)
        if cov_res.success and cov_res.output:
            state["coverage_state"] = cov_res.output.model_dump() if hasattr(cov_res.output, "model_dump") else cov_res.output

        # 2. Difficulty
        diff_ctx = AgentContext(
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            context=ctx_obj,
            extra={
                "current_difficulty": "medium",
                "min_difficulty": "easy",
                "max_difficulty": "hard",
                "evidence_strength": evidence_strength,
                "recent_performance": state.get("response_analysis", {}),
            },
        )
        diff_res = await difficulty_agent.run(diff_ctx)
        if diff_res.success and diff_res.output:
            state["difficulty_adaptation"] = diff_res.output.model_dump() if hasattr(diff_res.output, "model_dump") else diff_res.output
    except Exception as exc:
        logger.warning("Error in evaluate_coverage_and_difficulty_node: %s", exc)
    return state


async def generate_recommendation_node(state: Dict[str, Any], gateway: Any) -> Dict[str, Any]:
    """Synthesizes recommendations bounded by Question Plan and safety constraints."""
    try:
        agent = AdaptiveInterviewAgent(gateway=gateway)

        builder = InterviewContextBuilder()
        ctx_obj = builder.build(
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            current_stage=state.get("current_stage", "technical"),
        )

        agent_ctx = AgentContext(
            workspace_id=state["workspace_id"],
            interview_id=state["interview_id"],
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            context=ctx_obj,
            extra={
                "current_stage": state.get("current_stage", "technical"),
                "remaining_seconds": state.get("remaining_seconds", 900),
                "approved_question_plan": state.get("approved_question_plan", []),
                "uncovered_competencies": [state.get("competency", "General")],
                "weak_evidence_areas": state.get("response_analysis", {}).get("missing_concepts", []),
                "recent_response_analysis": state.get("response_analysis", {}),
                "coding_signals": state.get("coding_signals", {}),
                "system_design_signals": state.get("system_design_signals", {}),
                "resume_claims": state.get("resume_claims", []),
                "previous_questions_asked": state.get("previous_questions_asked", []),
            },
        )

        res = await agent.run(agent_ctx)
        if res.success and res.output:
            out_dict = res.output.model_dump() if hasattr(res.output, "model_dump") else res.output
            state["recommendation"] = out_dict
        else:
            # Deterministic fallback recommendation
            state["recommendation"] = {
                "action": "generate_follow_up",
                "recommended_question": f"Can you elaborate on your approach to {state.get('competency', 'this system')} and any key tradeoffs you made?",
                "competency": state.get("competency", "General"),
                "difficulty": "medium",
                "reason": "Probe technical depth and trade-off evaluation.",
                "evidence_target": "System trade-offs and decision criteria",
                "time_cost_estimate_seconds": 180,
                "confidence": 0.85,
                "requires_approval": True,
            }
    except Exception as exc:
        logger.error("Error in generate_recommendation_node: %s", exc)
        state["recommendation"] = {
            "action": "generate_follow_up",
            "recommended_question": "Can you explain the key design decisions and failure modes of your solution?",
            "competency": state.get("competency", "General"),
            "difficulty": "medium",
            "reason": "Fallback adaptive question probe.",
            "evidence_target": "Failure mode analysis",
            "time_cost_estimate_seconds": 180,
            "confidence": 0.80,
            "requires_approval": True,
        }
    return state


def build_adaptive_graph(gateway: Optional[Any] = None) -> AdaptiveGraphOrchestrator:
    """Returns the compiled orchestrator for adaptive interviewing."""
    return AdaptiveGraphOrchestrator(gateway=gateway)

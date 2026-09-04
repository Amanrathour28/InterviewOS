"""
AI Task Endpoints — Core AI Copilot API.

All endpoints require interviewer authentication.
Candidates must never be able to call these endpoints.

Endpoints:
  POST /ai/tasks                   - Run an AI task through the graph
  POST /ai/generate-question       - Generate an interview question
  POST /ai/generate-follow-up      - Generate a follow-up suggestion
  POST /ai/analyze-resume          - Analyze a candidate resume
  POST /ai/analyze-job             - Analyze a job description
  POST /ai/analyze-coding          - Analyze coding submission
  POST /ai/analyze-system-design   - Analyze whiteboard/system design
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import require_interviewer
from app.graphs.interview_graph import run_graph

logger = logging.getLogger("interviewos.ai.api.ai")
router = APIRouter()


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class AITaskRequest(BaseModel):
    """Generic AI task request routed through the graph."""

    interview_id: str
    session_id: Optional[str] = None
    workspace_id: str
    task_type: str
    input_data: Dict[str, Any] = Field(default_factory=dict)


class QuestionGenerationRequest(BaseModel):
    interview_id: str
    session_id: Optional[str] = None
    workspace_id: str
    difficulty: str = "medium"
    question_type: str = "technical"
    topic_focus: Optional[str] = None
    topics_covered: List[str] = Field(default_factory=list)
    candidate: Optional[Dict[str, Any]] = None
    job: Optional[Dict[str, Any]] = None
    previous_questions: List[str] = Field(default_factory=list)
    current_stage: Optional[str] = None


class FollowUpRequest(BaseModel):
    interview_id: str
    session_id: Optional[str] = None
    workspace_id: str
    question_asked: str
    candidate_answer: str
    target_skill: Optional[str] = None
    difficulty: str = "medium"
    remaining_seconds: int = 600


class ResumeAnalysisRequest(BaseModel):
    interview_id: str
    workspace_id: str
    resume_text: Optional[str] = None
    candidate_profile: Optional[Dict[str, Any]] = None
    job: Optional[Dict[str, Any]] = None


class JobAnalysisRequest(BaseModel):
    interview_id: str
    workspace_id: str
    job: Dict[str, Any]


class CodingAnalysisRequest(BaseModel):
    interview_id: str
    session_id: Optional[str] = None
    workspace_id: str
    problem: Optional[Dict[str, Any]] = None
    candidate_code: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    submission_history: List[Dict[str, Any]] = Field(default_factory=list)


class SystemDesignRequest(BaseModel):
    interview_id: str
    session_id: Optional[str] = None
    workspace_id: str
    whiteboard_state: Optional[Dict[str, Any]] = None
    candidate_explanation: Optional[str] = None
    problem_statement: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

async def _run_task(
    task_type: str,
    workspace_id: str,
    interview_id: str,
    caller: dict,
    input_data: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Shared helper that runs the LangGraph and returns the result."""
    request_id = str(uuid.uuid4())

    result = await run_graph(
        request_id=request_id,
        workspace_id=workspace_id,
        interview_id=interview_id,
        task_type=task_type,
        raw_input=input_data,
        is_interviewer=caller.get("is_interviewer", False),
        session_id=session_id,
        user_id=caller.get("user_id"),
    )

    if result.get("error"):
        error_type = result.get("error_type", "AIError")
        # Security/auth errors → 403
        if error_type in ("AIUnauthorizedError", "AITenantIsolationError"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result["error"])
        # All other AI errors → 200 with failed status (graceful degradation)
        return {
            "request_id": request_id,
            "status": "failed",
            "error_type": error_type,
            "error_message": result["error"],
            "output": None,
        }

    agent_result = result.get("agent_result", {})
    return {
        "request_id": request_id,
        "task_type": task_type,
        **agent_result,
    }


@router.post("/tasks")
async def run_ai_task(
    req: AITaskRequest,
    caller: dict = Depends(require_interviewer),
):
    """Generic AI task endpoint. Routes through the graph."""
    return await _run_task(
        task_type=req.task_type,
        workspace_id=req.workspace_id,
        interview_id=req.interview_id,
        caller=caller,
        input_data=req.input_data,
        session_id=req.session_id,
    )


@router.post("/generate-question")
async def generate_question(
    req: QuestionGenerationRequest,
    caller: dict = Depends(require_interviewer),
):
    """Generate an interview question. Interviewer-only."""
    return await _run_task(
        task_type="question_generation",
        workspace_id=req.workspace_id,
        interview_id=req.interview_id,
        caller=caller,
        session_id=req.session_id,
        input_data={
            "difficulty": req.difficulty,
            "type": req.question_type,
            "topic_focus": req.topic_focus,
            "topics_covered": req.topics_covered,
            "candidate": req.candidate,
            "job": req.job,
            "previous_questions": req.previous_questions,
            "current_stage": req.current_stage,
        },
    )


@router.post("/generate-follow-up")
async def generate_follow_up(
    req: FollowUpRequest,
    caller: dict = Depends(require_interviewer),
):
    """Generate a follow-up question suggestion. Interviewer-only."""
    return await _run_task(
        task_type="follow_up",
        workspace_id=req.workspace_id,
        interview_id=req.interview_id,
        caller=caller,
        session_id=req.session_id,
        input_data={
            "question_asked": req.question_asked,
            "candidate_answer": req.candidate_answer,
            "target_skill": req.target_skill,
            "difficulty": req.difficulty,
            "remaining_seconds": req.remaining_seconds,
        },
    )


@router.post("/analyze-resume")
async def analyze_resume(
    req: ResumeAnalysisRequest,
    caller: dict = Depends(require_interviewer),
):
    """Analyze a candidate resume. Interviewer-only."""
    return await _run_task(
        task_type="resume_analysis",
        workspace_id=req.workspace_id,
        interview_id=req.interview_id,
        caller=caller,
        input_data={
            "resume_text": req.resume_text,
            "candidate_profile": req.candidate_profile,
            "job": req.job,
        },
    )


@router.post("/analyze-job")
async def analyze_job(
    req: JobAnalysisRequest,
    caller: dict = Depends(require_interviewer),
):
    """Analyze a job description. Interviewer-only."""
    return await _run_task(
        task_type="jd_analysis",
        workspace_id=req.workspace_id,
        interview_id=req.interview_id,
        caller=caller,
        input_data={"job": req.job},
    )


@router.post("/analyze-coding")
async def analyze_coding(
    req: CodingAnalysisRequest,
    caller: dict = Depends(require_interviewer),
):
    """Analyze a coding submission. Interviewer-only. Sandbox results are authoritative."""
    return await _run_task(
        task_type="coding_analysis",
        workspace_id=req.workspace_id,
        interview_id=req.interview_id,
        caller=caller,
        session_id=req.session_id,
        input_data={
            "problem": req.problem,
            "candidate_code": req.candidate_code,
            "execution_result": req.execution_result,
            "submission_history": req.submission_history,
        },
    )


@router.post("/analyze-system-design")
async def analyze_system_design(
    req: SystemDesignRequest,
    caller: dict = Depends(require_interviewer),
):
    """Analyze system design whiteboard. Interviewer-only."""
    return await _run_task(
        task_type="system_design_analysis",
        workspace_id=req.workspace_id,
        interview_id=req.interview_id,
        caller=caller,
        session_id=req.session_id,
        input_data={
            "whiteboard_state": req.whiteboard_state,
            "candidate_explanation": req.candidate_explanation,
            "problem_statement": req.problem_statement,
        },
    )


# ---------------------------------------------------------------------------
# Phase 16 — Analytics Explanation (internal call from API service)
# ---------------------------------------------------------------------------

class AnalyticsExplainRequest(BaseModel):
    workspace_id: str
    metrics: Dict[str, Any]
    question: str = Field(max_length=500)
    context_label: str = Field(default="analytics", max_length=80)


@router.post("/analytics/explain")
async def analytics_explain(req: AnalyticsExplainRequest):
    """
    Advisory analytics explanation endpoint.
    Called internally by the API service. Returns structured explanation.
    AI interprets deterministic metrics only — never invents values.
    """
    try:
        from app.agents.analytics_explanation_agent import analytics_explanation_agent

        explanation = await analytics_explanation_agent.explain_metrics(
            workspace_id=req.workspace_id,
            metrics=req.metrics,
            question=req.question,
            context_label=req.context_label,
        )

        valid = analytics_explanation_agent.validate_explanation(explanation, req.metrics)
        if not valid:
            explanation = "[Explanation unavailable: potential content policy violation detected.]"

        return {
            "explanation": explanation,
            "disclaimer": (
                "This explanation is advisory only. All metric values are computed deterministically "
                "by the analytics engine and are not modified by the AI explanation layer."
            ),
        }
    except Exception as exc:
        logger.warning("Analytics explain failed: %s", exc)
        return {
            "explanation": "AI explanation temporarily unavailable.",
            "disclaimer": (
                "This explanation is advisory only. All metric values are computed deterministically "
                "by the analytics engine."
            ),
        }

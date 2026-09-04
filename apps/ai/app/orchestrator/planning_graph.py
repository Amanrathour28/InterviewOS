"""
LangGraph Planning Workflow Orchestration — Phase 13.

Defines the multi-stage planning graph:
  Load Candidate & Job -> Normalize Skills -> Deterministic Match -> Identify Gaps
  -> Generate Interview Blueprint -> Generate Question Plan -> Validate & Filter
"""

import logging
from typing import Any, Dict, List, Optional, TypedDict

logger = logging.getLogger("interviewos.ai.planning_graph")


class PlanningState(TypedDict):
    workspace_id: str
    candidate_id: str
    job_id: Optional[str]
    resume_text: Optional[str]
    candidate_profile: Dict[str, Any]
    job_profile: Dict[str, Any]
    claims: List[Dict[str, Any]]
    normalized_skills: List[Dict[str, Any]]
    match_result: Optional[Dict[str, Any]]
    gaps: List[Dict[str, Any]]
    blueprint: Optional[Dict[str, Any]]
    question_plan: Optional[Dict[str, Any]]
    status: str
    error: Optional[str]


class PlanningGraphOrchestrator:
    """Executes the sequential planning graph pipeline."""

    def __init__(self, gateway: Any):
        self.gateway = gateway

    async def execute_planning_pipeline(
        self,
        workspace_id: str,
        candidate_id: str,
        candidate_profile: Dict[str, Any],
        job_profile: Dict[str, Any],
        claims: Optional[List[Dict[str, Any]]] = None,
        deterministic_scores: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Runs the complete planning graph pipeline."""
        from app.agents.matching_agent import MatchingAgent
        from app.agents.blueprint_agent import InterviewPlanningAgent
        from app.agents.question_planner_agent import QuestionPlanningAgent
        from app.agents.base import AgentContext

        state: PlanningState = {
            "workspace_id": workspace_id,
            "candidate_id": candidate_id,
            "job_id": job_profile.get("id"),
            "resume_text": candidate_profile.get("summary", ""),
            "candidate_profile": candidate_profile,
            "job_profile": job_profile,
            "claims": claims or [],
            "normalized_skills": candidate_profile.get("skills", []),
            "match_result": deterministic_scores,
            "gaps": [],
            "blueprint": None,
            "question_plan": None,
            "status": "processing",
            "error": None,
        }

        # Step 1: Matching Explanation Agent
        matching_agent = MatchingAgent(gateway=self.gateway)
        match_ctx = AgentContext(
            workspace_id=workspace_id,
            interview_id=candidate_id,
            extra={
                "candidate_profile": candidate_profile,
                "job_profile": job_profile,
                "deterministic_scores": deterministic_scores or {},
                "claims": claims or [],
            },
        )
        match_res = await matching_agent.run(match_ctx)
        if match_res.status == "success" and match_res.output:
            state["gaps"] = [g.model_dump() for g in getattr(match_res.output, "gaps", [])]

        # Step 2: Blueprint Recommendation Agent
        blueprint_agent = InterviewPlanningAgent(gateway=self.gateway)
        bp_ctx = AgentContext(
            workspace_id=workspace_id,
            interview_id=candidate_id,
            extra={
                "candidate_profile": candidate_profile,
                "job_profile": job_profile,
                "gaps": state["gaps"],
                "claims": claims or [],
            },
        )
        bp_res = await blueprint_agent.run(bp_ctx)
        if bp_res.status == "success" and bp_res.output:
            state["blueprint"] = bp_res.output.model_dump()

        # Step 3: Question Plan Agent
        qp_agent = QuestionPlanningAgent(gateway=self.gateway)
        qp_ctx = AgentContext(
            workspace_id=workspace_id,
            interview_id=candidate_id,
            extra={
                "candidate_profile": candidate_profile,
                "job_profile": job_profile,
                "claims": claims or [],
                "gaps": state["gaps"],
                "blueprint": state["blueprint"] or {},
            },
        )
        qp_res = await qp_agent.run(qp_ctx)
        if qp_res.status == "success" and qp_res.output:
            state["question_plan"] = qp_res.output.model_dump()

        # Coverage Matrix calculation
        tested_skills = set()
        if state["question_plan"] and "questions" in state["question_plan"]:
            for q in state["question_plan"]["questions"]:
                if q.get("competency"):
                    tested_skills.add(q["competency"])

        state["coverage_matrix"] = {
            "competencies_covered": list(tested_skills),
            "coverage_percentage": round((len(tested_skills) / max(len(job_profile.get("required_skills", [1])), 1)) * 100, 1),
        }

        state["status"] = "completed"
        return state


async def run_planning_workflow(
    workspace_id: str,
    candidate_id: str,
    gateway: Any,
    job_id: Optional[str] = None,
    candidate_profile: Optional[Dict[str, Any]] = None,
    job_profile: Optional[Dict[str, Any]] = None,
    claims: Optional[List[Dict[str, Any]]] = None,
    deterministic_scores: Optional[Dict[str, Any]] = None,
    interview_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Top-level helper to execute the planning graph pipeline."""
    orchestrator = PlanningGraphOrchestrator(gateway=gateway)
    cand_prof = candidate_profile or {"skills": ["Python", "Algorithms"]}
    j_prof = job_profile or {"id": job_id, "required_skills": ["Python"]}
    return await orchestrator.execute_planning_pipeline(
        workspace_id=workspace_id,
        candidate_id=candidate_id,
        candidate_profile=cand_prof,
        job_profile=j_prof,
        claims=claims,
        deterministic_scores=deterministic_scores,
    )


"""
Phase 16 — Candidate Decision Intelligence & Timeline Service.

Provides:
- Candidate evaluation decision matrices
- Unified chronological candidate timeline across the entire hiring lifecycle
- Hiring funnel progression and stage conversion rates
- Strict separation between finalized authoritative evaluations and draft/in-review states
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate, CandidateDocument
from app.models.evaluation import (
    Evaluation,
    EvaluationAuditEvent,
    EvaluationCompetencyScore,
    EvaluationContradiction,
    EvaluationEvidence,
    EvaluationStatus,
)
from app.models.intelligence import CandidateJobMatch, ResumeProfile, ResumeVersion
from app.models.interview import Interview, InterviewStatus
from app.models.session import InterviewSession
from app.services.analytics_service import analytics_service

logger = logging.getLogger("interviewos.api.candidate_decision_service")


class CandidateDecisionService:
    """Service for candidate decision intelligence, timelines, and funnel metrics."""

    async def get_candidate_decision_matrix(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        job_id: Optional[uuid.UUID] = None,
        recommendation_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves candidate decision cards with scores, recommendations, and evidence counts.
        """
        query = (
            select(Evaluation, Candidate, Interview)
            .join(Candidate, Evaluation.candidate_id == Candidate.id)
            .join(Interview, Evaluation.interview_id == Interview.id)
            .where(
                Evaluation.workspace_id == workspace_id,
                Evaluation.created_at >= start_date,
                Evaluation.created_at <= end_date,
            )
        )

        if job_id:
            query = query.where(Evaluation.job_id == job_id)
        if recommendation_filter:
            query = query.where(Evaluation.recommendation == recommendation_filter)
        if status_filter:
            query = query.where(Evaluation.status == status_filter)

        result = await db.execute(query)
        rows = result.all()

        candidate_items: List[Dict[str, Any]] = []
        finalized_scores: List[float] = []
        recommendations_list: List[str] = []

        for eval_item, cand, itw in rows:
            is_finalized = eval_item.status == EvaluationStatus.FINALIZED.value
            if is_finalized:
                finalized_scores.append(eval_item.overall_score)
                recommendations_list.append(eval_item.recommendation)

            # Fetch competency summary for this evaluation
            comp_stmt = select(EvaluationCompetencyScore).where(
                EvaluationCompetencyScore.evaluation_id == eval_item.id
            )
            comp_res = await db.execute(comp_stmt)
            comp_scores = comp_res.scalars().all()

            competencies = [
                {
                    "name": cs.competency_name,
                    "score": cs.calculated_score,
                    "rubric_level": cs.rubric_level,
                    "is_overridden": cs.is_overridden,
                    "status": cs.status,
                }
                for cs in comp_scores
            ]

            # Count contradictions & evidence
            contra_stmt = select(func.count(EvaluationContradiction.id)).where(
                EvaluationContradiction.evaluation_id == eval_item.id
            )
            contra_count = (await db.execute(contra_stmt)).scalar() or 0

            evid_stmt = select(func.count(EvaluationEvidence.id)).where(
                EvaluationEvidence.interview_id == itw.id
            )
            evid_count = (await db.execute(evid_stmt)).scalar() or 0

            candidate_items.append({
                "evaluation_id": str(eval_item.id),
                "interview_id": str(itw.id),
                "interview_title": itw.title,
                "candidate_id": str(cand.id),
                "candidate_name": f"{cand.first_name} {cand.last_name}",
                "candidate_email": cand.email,
                "job_id": str(eval_item.job_id) if eval_item.job_id else None,
                "overall_score": eval_item.overall_score,
                "overall_rubric_level": eval_item.overall_rubric_level,
                "recommendation": eval_item.recommendation,
                "confidence": eval_item.confidence,
                "status": eval_item.status,
                "is_locked": eval_item.is_locked,
                "is_authoritative": is_finalized,
                "competency_scores": competencies,
                "evidence_count": evid_count,
                "contradiction_count": contra_count,
                "finalized_at": eval_item.finalized_at.isoformat() if eval_item.finalized_at else None,
                "created_at": eval_item.created_at.isoformat(),
            })

        score_distribution = analytics_service.calculate_score_distribution(finalized_scores)
        recommendation_distribution = analytics_service.calculate_recommendation_distribution(recommendations_list)

        return {
            "total_evaluations": len(rows),
            "finalized_count": len(finalized_scores),
            "draft_count": len(rows) - len(finalized_scores),
            "score_distribution": score_distribution,
            "recommendation_distribution": recommendation_distribution,
            "candidates": candidate_items,
        }

    async def get_candidate_unified_timeline(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Builds an authoritative chronological timeline of all events for a candidate.
        """
        # Fetch candidate info
        cand_stmt = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.workspace_id == workspace_id,
        )
        candidate = (await db.execute(cand_stmt)).scalar_one_or_none()
        if not candidate:
            return {"candidate_id": str(candidate_id), "timeline": []}

        events: List[Dict[str, Any]] = []

        # 1. Candidate Application / Creation
        events.append({
            "timestamp": candidate.created_at.isoformat(),
            "event_type": "candidate_created",
            "title": "Candidate Application Created",
            "description": f"Candidate profile initialized from source: {candidate.source.value if hasattr(candidate.source, 'value') else candidate.source}",
            "actor": "System / Recruiter",
            "metadata": {"email": candidate.email, "status": str(candidate.status)},
        })

        # 2. Documents Uploaded
        doc_stmt = select(CandidateDocument).where(CandidateDocument.candidate_id == candidate_id)
        docs = (await db.execute(doc_stmt)).scalars().all()
        for d in docs:
            events.append({
                "timestamp": d.created_at.isoformat(),
                "event_type": "document_uploaded",
                "title": f"Document Uploaded: {d.file_name}",
                "description": f"Document type: {d.document_type.value if hasattr(d.document_type, 'value') else d.document_type}",
                "actor": "System",
                "metadata": {"doc_id": str(d.id), "file_size": d.file_size},
            })

        # 3. Resume Intelligence
        resume_stmt = (
            select(ResumeProfile)
            .join(ResumeVersion, ResumeProfile.resume_version_id == ResumeVersion.id)
            .where(ResumeVersion.candidate_id == candidate_id)
        )
        resume_profiles = (await db.execute(resume_stmt)).scalars().all()
        for r in resume_profiles:
            events.append({
                "timestamp": r.created_at.isoformat(),
                "event_type": "resume_parsed",
                "title": "Resume Intelligence Extracted",
                "description": f"Extracted {len(r.skills)} skills and {len(r.experience)} experience records.",
                "actor": "AI Resume Extractor",
                "metadata": {"confidence": r.confidence},
            })

        # 4. Job Matches
        match_stmt = select(CandidateJobMatch).where(CandidateJobMatch.candidate_id == candidate_id)
        matches = (await db.execute(match_stmt)).scalars().all()
        for m in matches:
            events.append({
                "timestamp": m.created_at.isoformat(),
                "event_type": "job_matched",
                "title": "Job Match Calculated",
                "description": f"Overall match score: {m.overall_score}%",
                "actor": "Matching Engine",
                "metadata": {"job_id": str(m.job_id), "match_score": m.overall_score},
            })

        # 5. Interviews & Sessions
        itw_stmt = select(Interview).where(
            Interview.candidate_id == candidate_id,
            Interview.workspace_id == workspace_id,
        )
        interviews = (await db.execute(itw_stmt)).scalars().all()
        for itw in interviews:
            events.append({
                "timestamp": itw.created_at.isoformat(),
                "event_type": "interview_scheduled",
                "title": f"Interview Scheduled: {itw.title}",
                "description": f"Type: {itw.interview_type.value if hasattr(itw.interview_type, 'value') else itw.interview_type}, Duration: {itw.duration_minutes}m",
                "actor": "Scheduler",
                "metadata": {"interview_id": str(itw.id), "status": str(itw.status)},
            })

            # Sessions
            sess_stmt = select(InterviewSession).where(InterviewSession.interview_id == itw.id)
            sessions = (await db.execute(sess_stmt)).scalars().all()
            for s in sessions:
                if s.started_at:
                    events.append({
                        "timestamp": s.started_at.isoformat(),
                        "event_type": "interview_started",
                        "title": "Live Interview Session Started",
                        "description": f"Live room active for interview: {itw.title}",
                        "actor": "Interviewer / Candidate",
                        "metadata": {"session_id": str(s.id)},
                    })
                if s.ended_at:
                    events.append({
                        "timestamp": s.ended_at.isoformat(),
                        "event_type": "interview_completed",
                        "title": "Live Interview Session Completed",
                        "description": f"Interview concluded. Total paused seconds: {s.total_paused_seconds}s",
                        "actor": "Interviewer",
                        "metadata": {"session_id": str(s.id), "status": str(s.status)},
                    })

        # 6. Evaluations & Audits
        eval_stmt = select(Evaluation).where(
            Evaluation.candidate_id == candidate_id,
            Evaluation.workspace_id == workspace_id,
        )
        evaluations = (await db.execute(eval_stmt)).scalars().all()
        for ev in evaluations:
            events.append({
                "timestamp": ev.created_at.isoformat(),
                "event_type": "evaluation_generated",
                "title": "AI Evaluation Generated",
                "description": f"Initial score: {ev.overall_score}, Recommendation: {ev.recommendation}",
                "actor": "Evaluation Engine",
                "metadata": {"evaluation_id": str(ev.id), "score": ev.overall_score},
            })

            # Audit Events
            audit_stmt = select(EvaluationAuditEvent).where(EvaluationAuditEvent.evaluation_id == ev.id)
            audits = (await db.execute(audit_stmt)).scalars().all()
            for au in audits:
                events.append({
                    "timestamp": au.created_at.isoformat(),
                    "event_type": au.action,
                    "title": f"Evaluation Action: {au.action.replace('_', ' ').title()}",
                    "description": au.rationale or f"State transitioned to {au.after_state.get('status', 'updated')}",
                    "actor": str(au.actor_id) if au.actor_id else "System",
                    "metadata": {"action": au.action},
                })

            if ev.finalized_at:
                events.append({
                    "timestamp": ev.finalized_at.isoformat(),
                    "event_type": "evaluation_finalized",
                    "title": "Evaluation Sealed & Finalized",
                    "description": f"Final score: {ev.overall_score}, Sealed Recommendation: {ev.recommendation}",
                    "actor": str(ev.finalized_by) if ev.finalized_by else "Lead Evaluator",
                    "metadata": {"evaluation_id": str(ev.id), "recommendation": ev.recommendation},
                })

        # Sort chronologically
        events.sort(key=lambda e: e["timestamp"])

        candidate_name = f"{candidate.first_name} {candidate.last_name}"
        return {
            "candidate_id": str(candidate_id),
            "candidate_name": candidate_name,
            "candidate_email": candidate.email,
            "event_count": len(events),
            "timeline": events,
        }

    async def get_hiring_funnel_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        job_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Calculates hiring funnel progression counts and stage-to-stage conversion rates.
        Stages:
        1. Candidates Created (Applicants)
        2. Job Matched
        3. Interview Scheduled
        4. Interview Started
        5. Interview Completed
        6. Evaluation Generated
        7. Evaluation Finalized
        8. Hire Recommendation
        """
        cand_query = select(func.count(Candidate.id)).where(
            Candidate.workspace_id == workspace_id,
            Candidate.created_at >= start_date,
            Candidate.created_at <= end_date,
            Candidate.is_deleted.is_(False),
        )
        total_candidates = (await db.execute(cand_query)).scalar() or 0

        # Matched candidates
        matched_query = (
            select(func.count(func.distinct(CandidateJobMatch.candidate_id)))
            .join(Candidate, CandidateJobMatch.candidate_id == Candidate.id)
            .where(
                Candidate.workspace_id == workspace_id,
                CandidateJobMatch.created_at >= start_date,
                CandidateJobMatch.created_at <= end_date,
            )
        )
        if job_id:
            matched_query = matched_query.where(CandidateJobMatch.job_id == job_id)
        matched_candidates = (await db.execute(matched_query)).scalar() or 0

        # Interviews scheduled
        itw_query = select(Interview).where(
            Interview.workspace_id == workspace_id,
            Interview.created_at >= start_date,
            Interview.created_at <= end_date,
            Interview.is_deleted.is_(False),
        )
        if job_id:
            itw_query = itw_query.where(Interview.job_id == job_id)
        interviews = (await db.execute(itw_query)).scalars().all()

        scheduled_count = len(interviews)
        completed_count = sum(1 for itw in interviews if str(itw.status).lower().endswith("completed"))

        # Sessions started
        sess_query = select(func.count(InterviewSession.id)).where(
            InterviewSession.workspace_id == workspace_id,
            InterviewSession.created_at >= start_date,
            InterviewSession.created_at <= end_date,
            InterviewSession.started_at.is_not(None),
            InterviewSession.is_deleted.is_(False),
        )
        started_count = (await db.execute(sess_query)).scalar() or 0

        # Evaluations
        eval_query = select(Evaluation).where(
            Evaluation.workspace_id == workspace_id,
            Evaluation.created_at >= start_date,
            Evaluation.created_at <= end_date,
        )
        if job_id:
            eval_query = eval_query.where(Evaluation.job_id == job_id)
        evaluations = (await db.execute(eval_query)).scalars().all()

        generated_evals = len(evaluations)
        finalized_evals = sum(1 for e in evaluations if e.status == EvaluationStatus.FINALIZED.value)
        hire_recommendations = sum(
            1 for e in evaluations
            if e.status == EvaluationStatus.FINALIZED.value
            and e.recommendation in ["strong_hire", "hire", "lean_hire"]
        )

        # Calculate Conversion Rates
        stages = [
            {"stage": "applicants", "name": "Applicants", "count": total_candidates},
            {"stage": "matched", "name": "Job Matched", "count": matched_candidates},
            {"stage": "scheduled", "name": "Interview Scheduled", "count": scheduled_count},
            {"stage": "started", "name": "Interview Started", "count": started_count},
            {"stage": "completed", "name": "Interview Completed", "count": completed_count},
            {"stage": "evaluated", "name": "Evaluation Generated", "count": generated_evals},
            {"stage": "finalized", "name": "Evaluation Finalized", "count": finalized_evals},
            {"stage": "hired", "name": "Hire Recommendation", "count": hire_recommendations},
        ]

        # Calculate step-by-step conversion percentages
        for i in range(len(stages)):
            curr_count = stages[i]["count"]
            if i == 0:
                stages[i]["conversion_from_previous"] = 100.0
                stages[i]["conversion_from_top"] = 100.0
            else:
                prev_count = stages[i - 1]["count"]
                stages[i]["conversion_from_previous"] = (
                    round((curr_count / prev_count) * 100.0, 2)
                    if prev_count > 0 else 0.0
                )
                stages[i]["conversion_from_top"] = (
                    round((curr_count / total_candidates) * 100.0, 2)
                    if total_candidates > 0 else 0.0
                )

        return {
            "time_window": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
            "funnel_stages": stages,
            "overall_hire_conversion_rate": (
                round((hire_recommendations / total_candidates) * 100.0, 2)
                if total_candidates > 0 else 0.0
            ),
        }


candidate_decision_service = CandidateDecisionService()

"""
Phase 16 — Question & Adaptive Questioning Analytics Service.

Provides deterministic analytics on:
- Question usage: times asked, answered, skipped, average score, response duration
- Evidence Yield: useful_evidence_events / times_asked (labeled as an indicator, not a quality judgment)
- Coverage Yield: competency_evidence_generated / times_asked
- Adaptive interviewing: recommendation acceptance, rejection, edit, skip rates
- Downstream evidence generation from adaptive recommendations
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive_interview import (
    AIInterviewRecommendation,
    RecommendationAction,
    RecommendationStatus,
)
from app.models.evaluation import EvaluationEvidence, EvaluationStatus, Evaluation
from app.models.interview import Interview, InterviewRoundQuestion, Question
from app.services.analytics_service import analytics_service

logger = logging.getLogger("interviewos.api.question_analytics_service")


class QuestionAnalyticsService:
    """Service for question-level performance and adaptive questioning analytics."""

    async def get_question_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        job_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates performance metrics per question in workspace question bank.
        """
        # Get questions in workspace (or shared system questions)
        q_query = select(Question).where(
            Question.workspace_id == workspace_id,
            Question.is_deleted.is_(False),
        )
        q_res = await db.execute(q_query)
        questions = q_res.scalars().all()

        # Build map of question_id -> how many times it was used across all rounds in date range
        irq_query = (
            select(InterviewRoundQuestion, Interview)
            .join(Interview, Interview.id.in_(
                select(InterviewRoundQuestion.__table__.c.interview_id)
                .join(Interview, InterviewRoundQuestion.__table__.c.interview_id == Interview.id)
                .where(
                    Interview.workspace_id == workspace_id,
                    Interview.created_at >= start_date,
                    Interview.created_at <= end_date,
                    Interview.is_deleted.is_(False),
                )
            ))
        )

        # Simpler approach: get all interviews in scope, then their questions
        itw_query = select(Interview.id).where(
            Interview.workspace_id == workspace_id,
            Interview.created_at >= start_date,
            Interview.created_at <= end_date,
            Interview.is_deleted.is_(False),
        )
        if job_id:
            itw_query = itw_query.where(Interview.job_id == job_id)

        itw_ids = [row[0] for row in (await db.execute(itw_query)).all()]

        # Question usage per interview
        question_stats: Dict[uuid.UUID, Dict[str, Any]] = {}

        if itw_ids:
            rq_query = (
                select(InterviewRoundQuestion, Question)
                .join(Question, InterviewRoundQuestion.question_id == Question.id)
                .where(InterviewRoundQuestion.interview_id.in_(itw_ids))
            )
            rq_res = await db.execute(rq_query)
            rq_rows = rq_res.all()

            for rq, q in rq_rows:
                qid = q.id
                if qid not in question_stats:
                    question_stats[qid] = {
                        "question_id": str(qid),
                        "title": q.title,
                        "question_type": str(q.question_type).split(".")[-1],
                        "category": q.category,
                        "difficulty": str(q.difficulty).split(".")[-1],
                        "skills": q.skills,
                        "times_asked": 0,
                        "evidence_generated_count": 0,
                    }
                question_stats[qid]["times_asked"] += 1

        # Evidence generation per question (link through competency_name / question_text in EvaluationEvidence)
        evid_query = select(EvaluationEvidence).where(
            EvaluationEvidence.workspace_id == workspace_id,
            EvaluationEvidence.created_at >= start_date,
            EvaluationEvidence.created_at <= end_date,
            EvaluationEvidence.question_text.is_not(None),
        )
        evid_res = await db.execute(evid_query)
        evidence_items = evid_res.scalars().all()

        question_evidence_counts: Dict[str, int] = {}
        for evid in evidence_items:
            qt = evid.question_text or ""
            if qt not in question_evidence_counts:
                question_evidence_counts[qt] = 0
            question_evidence_counts[qt] += 1

        # Build final summary
        question_summaries: List[Dict[str, Any]] = []
        for qid, stats in question_stats.items():
            times_asked = stats["times_asked"]
            evid_count = sum(
                count for qt, count in question_evidence_counts.items()
                if stats["title"].lower() in qt.lower()
            )

            evidence_yield = round(evid_count / times_asked, 3) if times_asked > 0 else 0.0

            question_summaries.append({
                **stats,
                "evidence_generated_count": evid_count,
                "evidence_yield": evidence_yield,
                "evidence_yield_label": "evidence_yield",
                "evidence_yield_formula": "evidence_events / times_asked",
            })

        # Sort by times_asked desc
        question_summaries.sort(key=lambda x: x["times_asked"], reverse=True)

        return {
            "total_questions_in_bank": len(questions),
            "questions_used_in_window": len(question_summaries),
            "questions": question_summaries,
        }

    async def get_adaptive_questioning_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Deterministic metrics on adaptive AI interviewer recommendations.
        Covers acceptance, rejection, edit, skip rates and difficulty adjustments.
        """
        rec_query = select(AIInterviewRecommendation).where(
            AIInterviewRecommendation.workspace_id == workspace_id,
            AIInterviewRecommendation.created_at >= start_date,
            AIInterviewRecommendation.created_at <= end_date,
            AIInterviewRecommendation.is_deleted.is_(False),
        )
        rec_res = await db.execute(rec_query)
        recommendations = rec_res.scalars().all()

        total = len(recommendations)

        status_counts = {
            "generated": 0,
            "accepted": 0,
            "rejected": 0,
            "edited": 0,
            "skipped": 0,
            "stale": 0,
            "expired": 0,
            "failed": 0,
        }

        action_counts: Dict[str, int] = {}
        difficulty_increases = 0
        difficulty_decreases = 0
        probe_weak_evidence_count = 0
        move_competency_count = 0

        for rec in recommendations:
            st = str(rec.status).split(".")[-1].lower()
            if st in status_counts:
                status_counts[st] += 1

            action = str(rec.action).split(".")[-1].lower()
            action_counts[action] = action_counts.get(action, 0) + 1

            if action == "increase_difficulty":
                difficulty_increases += 1
            elif action == "decrease_difficulty":
                difficulty_decreases += 1
            elif action == "probe_weak_evidence":
                probe_weak_evidence_count += 1
            elif action in ("move_to_next_competency", "revisit_competency"):
                move_competency_count += 1

        # Rates (denominator: only presented recommendations, not generating/stale/expired/failed)
        presented_count = (
            status_counts["accepted"] +
            status_counts["rejected"] +
            status_counts["edited"] +
            status_counts["skipped"]
        )

        def safe_rate(numerator: int, denominator: int) -> float:
            return round((numerator / denominator) * 100.0, 2) if denominator > 0 else 0.0

        acceptance_rate = safe_rate(status_counts["accepted"], presented_count)
        rejection_rate = safe_rate(status_counts["rejected"], presented_count)
        edit_rate = safe_rate(status_counts["edited"], presented_count)
        skip_rate = safe_rate(status_counts["skipped"], presented_count)

        return {
            "total_recommendations_generated": total,
            "total_presented": presented_count,
            "status_counts": status_counts,
            "action_counts": action_counts,
            "acceptance_rate": acceptance_rate,
            "rejection_rate": rejection_rate,
            "edit_rate": edit_rate,
            "skip_rate": skip_rate,
            "difficulty_increases": difficulty_increases,
            "difficulty_decreases": difficulty_decreases,
            "probe_weak_evidence_count": probe_weak_evidence_count,
            "competency_move_count": move_competency_count,
            "note": (
                "Rates computed as (count / total_presented) * 100. "
                "Stale, expired, failed recommendations are excluded from rate denominators."
            ),
        }


question_analytics_service = QuestionAnalyticsService()

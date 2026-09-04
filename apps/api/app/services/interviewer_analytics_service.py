"""
Phase 16 — Interviewer & Panel Analytics Service.

Provides:
- Interviewer activity (interviews conducted, completion rate, average duration)
- Score distribution and recommendation metrics per interviewer
- Objective calibration signals comparing individual interviewer averages to workspace baselines
- Strict minimum sample size threshold (n >= 10) for calibration indicators
- Neutral, statistical terminology (no bias claims)
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation, EvaluationCompetencyScore, EvaluationStatus
from app.models.interview import Interview, InterviewParticipant, InterviewStatus, ParticipantRole
from app.models.session import InterviewSession, SessionStatus
from app.models.user import User
from app.services.analytics_service import analytics_service

logger = logging.getLogger("interviewos.api.interviewer_analytics_service")


class InterviewerAnalyticsService:
    """Service for interviewer activity and calibration analytics."""

    async def get_interviewer_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        min_sample_threshold: int = 10,
    ) -> Dict[str, Any]:
        """
        Calculates interviewer panel metrics and objective calibration indicators.
        """
        # 1. Fetch workspace baseline for finalized evaluations
        ws_eval_query = select(Evaluation).where(
            Evaluation.workspace_id == workspace_id,
            Evaluation.created_at >= start_date,
            Evaluation.created_at <= end_date,
            Evaluation.status == EvaluationStatus.FINALIZED.value,
        )
        ws_eval_res = await db.execute(ws_eval_query)
        ws_evals = ws_eval_res.scalars().all()
        ws_scores = [e.overall_score for e in ws_evals]
        ws_mean = round(sum(ws_scores) / len(ws_scores), 2) if ws_scores else 0.0

        # 2. Query interviewers via InterviewParticipant
        query = (
            select(InterviewParticipant, User, Interview)
            .join(User, InterviewParticipant.user_id == User.id)
            .join(Interview, InterviewParticipant.interview_id == Interview.id)
            .where(
                Interview.workspace_id == workspace_id,
                Interview.created_at >= start_date,
                Interview.created_at <= end_date,
                Interview.is_deleted.is_(False),
            )
        )
        result = await db.execute(query)
        rows = result.all()

        # Group by interviewer user_id
        interviewer_map: Dict[uuid.UUID, Dict[str, Any]] = {}

        for part, user, itw in rows:
            uid = user.id
            if uid not in interviewer_map:
                interviewer_map[uid] = {
                    "user_id": str(uid),
                    "full_name": user.full_name or user.email,
                    "email": user.email,
                    "role": part.participant_role.value if hasattr(part.participant_role, "value") else str(part.participant_role),
                    "interviews": [],
                    "interview_ids": set(),
                }
            if itw.id not in interviewer_map[uid]["interview_ids"]:
                interviewer_map[uid]["interview_ids"].add(itw.id)
                interviewer_map[uid]["interviews"].append(itw)

        interviewers_summary: List[Dict[str, Any]] = []

        for uid, data in interviewer_map.items():
            itw_list = data["interviews"]
            total_itws = len(itw_list)
            completed_itws = sum(1 for itw in itw_list if str(itw.status).lower().endswith("completed"))

            itw_ids = list(data["interview_ids"])

            # Evaluations for these interviews
            eval_query = select(Evaluation).where(
                Evaluation.interview_id.in_(itw_ids),
                Evaluation.status == EvaluationStatus.FINALIZED.value,
            )
            eval_res = await db.execute(eval_query)
            evals = eval_res.scalars().all()

            scores = [e.overall_score for e in evals]
            recs = [e.recommendation for e in evals]
            n_finalized = len(scores)

            score_dist = analytics_service.calculate_score_distribution(scores)
            rec_dist = analytics_service.calculate_recommendation_distribution(recs)

            interviewer_mean = score_dist["mean"]
            diff_from_ws = round(interviewer_mean - ws_mean, 2) if (n_finalized > 0 and ws_mean > 0) else 0.0

            # Calibration Indicator
            if n_finalized < min_sample_threshold:
                calibration_status = "INSUFFICIENT_SAMPLE"
                calibration_signal = f"Calibration insights require >= {min_sample_threshold} finalized interviews (current n={n_finalized})"
            elif abs(diff_from_ws) <= 5.0:
                calibration_status = "CALIBRATED"
                calibration_signal = "Score distribution aligned with workspace baseline (within +/-5 points)"
            elif diff_from_ws > 5.0:
                calibration_status = "UPWARD_VARIANCE"
                calibration_signal = f"Scores trend {diff_from_ws:+.1f} points higher than workspace baseline"
            else:
                calibration_status = "DOWNWARD_VARIANCE"
                calibration_signal = f"Scores trend {diff_from_ws:+.1f} points lower than workspace baseline"

            interviewers_summary.append({
                "user_id": data["user_id"],
                "full_name": data["full_name"],
                "email": data["email"],
                "interviews_conducted": total_itws,
                "interviews_completed": completed_itws,
                "finalized_evaluations_count": n_finalized,
                "average_score": interviewer_mean,
                "median_score": score_dist["median"],
                "score_distribution": score_dist,
                "recommendation_distribution": rec_dist,
                "workspace_baseline_mean": ws_mean,
                "difference_from_workspace_mean": diff_from_ws,
                "calibration_status": calibration_status,
                "calibration_signal": calibration_signal,
                "has_sufficient_sample": n_finalized >= min_sample_threshold,
            })

        return {
            "workspace_baseline_mean_score": ws_mean,
            "total_finalized_evaluations_in_workspace": len(ws_scores),
            "min_sample_threshold": min_sample_threshold,
            "interviewers_count": len(interviewers_summary),
            "interviewers": interviewers_summary,
        }


interviewer_analytics_service = InterviewerAnalyticsService()

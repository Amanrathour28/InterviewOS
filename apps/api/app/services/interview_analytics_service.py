"""
Phase 16 — Interview Analytics Service.

Provides deterministic calculations for:
- Interview volume (scheduled, started, completed, cancelled, expired, in_progress)
- Completion, cancellation, and no-show rates
- Scheduled vs actual duration distributions
- Stage-by-stage progression, duration, and abandonment analytics
- Daily/weekly volume trends
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import Interview, InterviewRound, InterviewStatus, InterviewType
from app.models.session import InterviewEvent, InterviewSession, SessionStatus
from app.services.analytics_service import analytics_service

logger = logging.getLogger("interviewos.api.interview_analytics_service")


class InterviewAnalyticsService:
    """Service for deterministic interview-level analytics."""

    async def get_interview_volume_and_rates(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        job_id: Optional[uuid.UUID] = None,
        interview_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates interview volume counts and deterministic completion/cancellation rates.
        """
        query = select(Interview).where(
            Interview.workspace_id == workspace_id,
            Interview.created_at >= start_date,
            Interview.created_at <= end_date,
            Interview.is_deleted.is_(False),
        )

        if job_id:
            query = query.where(Interview.job_id == job_id)
        if interview_type:
            query = query.where(Interview.interview_type == interview_type)

        result = await db.execute(query)
        interviews = result.scalars().all()

        total = len(interviews)
        status_counts = {
            "draft": 0,
            "ready": 0,
            "scheduled": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0,
            "expired": 0,
        }

        for item in interviews:
            st = str(item.status).lower().split(".")[-1]
            if st in status_counts:
                status_counts[st] += 1

        # Sessions for no-show calculation
        sess_query = select(InterviewSession).where(
            InterviewSession.workspace_id == workspace_id,
            InterviewSession.created_at >= start_date,
            InterviewSession.created_at <= end_date,
            InterviewSession.is_deleted.is_(False),
        )
        sess_result = await db.execute(sess_query)
        sessions = sess_result.scalars().all()

        started_count = sum(1 for s in sessions if s.started_at is not None)
        completed_sessions = sum(1 for s in sessions if str(s.status).lower().endswith("completed"))

        # Deterministic rates
        scheduled_or_started = status_counts["scheduled"] + status_counts["in_progress"] + status_counts["completed"]
        completion_rate = (
            round((status_counts["completed"] / total) * 100.0, 2)
            if total > 0 else 0.0
        )
        cancellation_rate = (
            round((status_counts["cancelled"] / total) * 100.0, 2)
            if total > 0 else 0.0
        )
        no_show_rate = (
            round((status_counts["expired"] / total) * 100.0, 2)
            if total > 0 else 0.0
        )

        return {
            "time_window": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
            "total": total,
            "total_interviews": total,
            "status_counts": status_counts,
            "completion_rate": completion_rate,
            "cancellation_rate": cancellation_rate,
            "no_show_rate": no_show_rate,
            "started_count": started_count,
            "completed_sessions": completed_sessions,
        }

    async def get_duration_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        job_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Calculates scheduled vs actual duration metrics for completed interview sessions.
        """
        query = (
            select(InterviewSession, Interview)
            .join(Interview, InterviewSession.interview_id == Interview.id)
            .where(
                InterviewSession.workspace_id == workspace_id,
                InterviewSession.created_at >= start_date,
                InterviewSession.created_at <= end_date,
                InterviewSession.status == SessionStatus.COMPLETED,
                InterviewSession.started_at.is_not(None),
                InterviewSession.ended_at.is_not(None),
                InterviewSession.is_deleted.is_(False),
            )
        )
        if job_id:
            query = query.where(Interview.job_id == job_id)

        result = await db.execute(query)
        rows = result.all()

        scheduled_durations: List[float] = []
        actual_durations: List[float] = []

        for sess, itw in rows:
            scheduled_durations.append(float(itw.duration_minutes))
            if sess.started_at and sess.ended_at:
                actual_minutes = (sess.ended_at - sess.started_at).total_seconds() / 60.0
                actual_minutes = max(1.0, actual_minutes - (sess.total_paused_seconds / 60.0))
                actual_durations.append(round(actual_minutes, 1))

        scheduled_dist = analytics_service.calculate_score_distribution(scheduled_durations)
        actual_dist = analytics_service.calculate_score_distribution(actual_durations)

        # Average variance (actual - scheduled)
        variance_minutes = (
            round(actual_dist["mean"] - scheduled_dist["mean"], 2)
            if scheduled_dist["sample_size"] > 0 else 0.0
        )

        return {
            "completed_sessions_sample_size": len(actual_durations),
            "scheduled_duration_stats": scheduled_dist,
            "actual_duration_stats": actual_dist,
            "mean_duration_variance_minutes": variance_minutes,
        }

    async def get_stage_progression_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Calculates stage-by-stage progression, duration, and abandonment statistics.
        """
        # Fetch interview rounds for workspace
        query = (
            select(InterviewRound)
            .join(Interview, InterviewRound.interview_id == Interview.id)
            .where(
                Interview.workspace_id == workspace_id,
                Interview.created_at >= start_date,
                Interview.created_at <= end_date,
                InterviewRound.is_deleted.is_(False),
            )
        )
        result = await db.execute(query)
        rounds = result.scalars().all()

        stage_types = ["technical", "coding", "system_design", "behavioral", "screening", "custom"]
        stage_counts = {k: 0 for k in stage_types}
        stage_durations: Dict[str, List[float]] = {k: [] for k in stage_types}

        for r in rounds:
            stype = str(r.round_type).lower().split(".")[-1]
            if stype not in stage_counts:
                stype = "custom"
            stage_counts[stype] += 1
            stage_durations[stype].append(float(r.duration_minutes))

        stage_stats = {}
        for stype in stage_types:
            durs = stage_durations[stype]
            avg_dur = round(sum(durs) / len(durs), 1) if durs else 0.0
            stage_stats[stype] = {
                "count": stage_counts[stype],
                "average_duration_minutes": avg_dur,
                "percentage_of_all_rounds": (
                    round((stage_counts[stype] / len(rounds)) * 100.0, 2)
                    if rounds else 0.0
                ),
            }

        return {
            "total_rounds_analyzed": len(rounds),
            "stages": stage_stats,
        }

    async def get_volume_timeline(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Groups interview creations and completions by date for time-series charts.
        """
        query = select(Interview).where(
            Interview.workspace_id == workspace_id,
            Interview.created_at >= start_date,
            Interview.created_at <= end_date,
            Interview.is_deleted.is_(False),
        ).order_by(Interview.created_at.asc())

        result = await db.execute(query)
        interviews = result.scalars().all()

        # Group by YYYY-MM-DD
        timeline_map: Dict[str, Dict[str, int]] = {}
        for itw in interviews:
            day_str = itw.created_at.strftime("%Y-%m-%d")
            if day_str not in timeline_map:
                timeline_map[day_str] = {"scheduled": 0, "completed": 0, "cancelled": 0}
            
            st = str(itw.status).lower().split(".")[-1]
            if st == "completed":
                timeline_map[day_str]["completed"] += 1
            elif st == "cancelled":
                timeline_map[day_str]["cancelled"] += 1
            else:
                timeline_map[day_str]["scheduled"] += 1

        timeline = [
            {
                "date": d,
                "scheduled": counts["scheduled"],
                "completed": counts["completed"],
                "cancelled": counts["cancelled"],
            }
            for d, counts in sorted(timeline_map.items())
        ]
        return timeline


interview_analytics_service = InterviewAnalyticsService()

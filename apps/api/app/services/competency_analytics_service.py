"""
Phase 16 — Competency Analytics Service.

Provides:
- Deterministic competency score distributions (mean, median, bins, percentiles)
- Evidence sufficiency rate and insufficient evidence frequency
- Human score override rates and rationale statistics
- Explicit sample size (n) calculations for every competency
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import (
    Evaluation,
    EvaluationCompetency,
    EvaluationCompetencyScore,
    EvaluationStatus,
)
from app.services.analytics_service import analytics_service

logger = logging.getLogger("interviewos.api.competency_analytics_service")


class CompetencyAnalyticsService:
    """Service for competency performance analytics."""

    async def get_competency_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        job_id: Optional[uuid.UUID] = None,
        finalized_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculates performance, score distributions, and override rates across competencies.
        """
        query = (
            select(EvaluationCompetencyScore, Evaluation)
            .join(Evaluation, EvaluationCompetencyScore.evaluation_id == Evaluation.id)
            .where(
                Evaluation.workspace_id == workspace_id,
                Evaluation.created_at >= start_date,
                Evaluation.created_at <= end_date,
            )
        )

        if finalized_only:
            query = query.where(Evaluation.status == EvaluationStatus.FINALIZED.value)
        if job_id:
            query = query.where(Evaluation.job_id == job_id)

        result = await db.execute(query)
        rows = result.all()

        # Group by competency name
        comp_map: Dict[str, List[EvaluationCompetencyScore]] = {}
        for cs, _ in rows:
            cname = cs.competency_name
            if cname not in comp_map:
                comp_map[cname] = []
            comp_map[cname].append(cs)

        competencies_summary: List[Dict[str, Any]] = []

        for cname, score_items in sorted(comp_map.items()):
            n = len(score_items)
            scores = [s.calculated_score for s in score_items]
            distribution = analytics_service.calculate_score_distribution(scores)

            # Sufficiency & Override
            assessed_count = sum(1 for s in score_items if s.status == "assessed")
            insufficient_count = sum(1 for s in score_items if s.status in ["insufficient_evidence", "not_assessed"])
            override_count = sum(1 for s in score_items if s.is_overridden)

            sufficiency_rate = round((assessed_count / n) * 100.0, 2) if n > 0 else 0.0
            insufficient_rate = round((insufficient_count / n) * 100.0, 2) if n > 0 else 0.0
            override_rate = round((override_count / n) * 100.0, 2) if n > 0 else 0.0

            # Rubric levels average
            avg_rubric_level = (
                round(sum(s.rubric_level for s in score_items) / n, 2)
                if n > 0 else 0.0
            )

            competencies_summary.append({
                "competency_name": cname,
                "sample_size": n,
                "average_score": distribution["mean"],
                "median_score": distribution["median"],
                "min_score": distribution["min"],
                "max_score": distribution["max"],
                "average_rubric_level": avg_rubric_level,
                "sufficiency_rate": sufficiency_rate,
                "insufficient_evidence_rate": insufficient_rate,
                "override_rate": override_rate,
                "override_count": override_count,
                "distribution": distribution,
            })

        return {
            "total_competency_evaluations": len(rows),
            "distinct_competencies_count": len(competencies_summary),
            "competencies": competencies_summary,
            "metadata": {
                "finalized_only": finalized_only,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }


competency_analytics_service = CompetencyAnalyticsService()

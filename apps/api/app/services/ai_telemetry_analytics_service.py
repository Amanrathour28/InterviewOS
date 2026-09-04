"""
Phase 16 — AI Telemetry & Evidence Quality Analytics Service.

Provides:
- AI gateway request telemetry: volume, success rate, fallback rate, latency distributions
- Provider/model/agent breakdowns
- Token usage aggregation (input, output, total — labeled as Estimated cost only)
- Evidence quality metrics: grounding status distribution, quote verification failure rates
- Contradiction analytics by source type and severity
"""

from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIRequestLog
from app.models.evaluation import (
    Evaluation,
    EvaluationCompetencyScore,
    EvaluationContradiction,
    EvaluationEvidence,
    EvaluationStatus,
)
from app.services.analytics_service import analytics_service

logger = logging.getLogger("interviewos.api.ai_telemetry_analytics_service")


class AITelemetryAnalyticsService:
    """Service for AI gateway telemetry and evidence quality analytics."""

    async def get_ai_telemetry_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        agent_filter: Optional[str] = None,
        provider_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates AI request telemetry within the workspace and time window.
        """
        query = select(AIRequestLog).where(
            AIRequestLog.workspace_id == str(workspace_id),
            AIRequestLog.created_at >= start_date,
            AIRequestLog.created_at <= end_date,
        )
        if agent_filter:
            query = query.where(AIRequestLog.agent_name == agent_filter)
        if provider_filter:
            query = query.where(AIRequestLog.provider == provider_filter)

        res = await db.execute(query)
        logs = res.scalars().all()

        total = len(logs)
        success_count = sum(1 for l in logs if l.success)
        failure_count = total - success_count
        fallback_count = sum(1 for l in logs if l.is_fallback)

        success_rate = round((success_count / total) * 100.0, 2) if total > 0 else 0.0
        failure_rate = round((failure_count / total) * 100.0, 2) if total > 0 else 0.0
        fallback_rate = round((fallback_count / total) * 100.0, 2) if total > 0 else 0.0

        # Latency distributions
        latencies = [l.latency_ms for l in logs if l.latency_ms is not None and l.latency_ms > 0]
        latency_stats = analytics_service.calculate_score_distribution(
            [float(lat) for lat in latencies]
        )

        # p95 latency
        p95_latency = latency_stats.get("p90", 0.0)  # using p90 bucket from distribution
        if latencies:
            sorted_lat = sorted(latencies)
            n = len(sorted_lat)
            p95_idx = min(int(math.ceil(0.95 * n)) - 1, n - 1)
            p95_latency = float(sorted_lat[p95_idx])

        # Provider / model / agent breakdowns
        provider_counts: Dict[str, int] = {}
        model_counts: Dict[str, int] = {}
        agent_counts: Dict[str, int] = {}

        for l in logs:
            p = l.provider or "unknown"
            m = l.model or "unknown"
            a = l.agent_name or "unknown"
            provider_counts[p] = provider_counts.get(p, 0) + 1
            model_counts[m] = model_counts.get(m, 0) + 1
            agent_counts[a] = agent_counts.get(a, 0) + 1

        # Token aggregation
        total_input_tokens = sum(l.input_tokens or 0 for l in logs)
        total_output_tokens = sum(l.output_tokens or 0 for l in logs)
        total_tokens = sum(l.total_tokens or 0 for l in logs)

        return {
            "time_window": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
            "total_requests": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "fallback_count": fallback_count,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "fallback_rate": fallback_rate,
            "latency_ms": {
                "mean": latency_stats["mean"],
                "median": latency_stats["median"],
                "min": latency_stats["min"],
                "max": latency_stats["max"],
                "p95": round(p95_latency, 2),
                "sample_size": latency_stats["sample_size"],
            },
            "token_usage": {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "note": "Estimated token counts from AI request logs. Accuracy depends on provider reporting.",
            },
            "provider_breakdown": dict(sorted(provider_counts.items(), key=lambda x: -x[1])),
            "model_breakdown": dict(sorted(model_counts.items(), key=lambda x: -x[1])),
            "agent_breakdown": dict(sorted(agent_counts.items(), key=lambda x: -x[1])),
        }

    async def get_evidence_quality_analytics(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        job_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates evidence quality metrics: grounding status distribution and
        contradiction rates by source type and severity.
        """
        eval_query = select(Evaluation).where(
            Evaluation.workspace_id == workspace_id,
            Evaluation.created_at >= start_date,
            Evaluation.created_at <= end_date,
            Evaluation.status == EvaluationStatus.FINALIZED.value,
        )
        if job_id:
            eval_query = eval_query.where(Evaluation.job_id == job_id)
        evals = (await db.execute(eval_query)).scalars().all()
        eval_ids = [e.id for e in evals]

        total_evals = len(evals)

        # Competency score grounding signals (using is_overridden as proxy for unsupported claim)
        comp_query = select(EvaluationCompetencyScore).where(
            EvaluationCompetencyScore.evaluation_id.in_(eval_ids)
        ) if eval_ids else None

        total_comp_scores = 0
        override_count = 0
        insufficient_count = 0
        if comp_query is not None:
            comp_res = await db.execute(comp_query)
            comp_scores = comp_res.scalars().all()
            total_comp_scores = len(comp_scores)
            override_count = sum(1 for cs in comp_scores if cs.is_overridden)
            insufficient_count = sum(1 for cs in comp_scores if cs.status == "insufficient_evidence")

        # Contradictions
        contra_query = select(EvaluationContradiction).where(
            EvaluationContradiction.evaluation_id.in_(eval_ids)
        ) if eval_ids else None

        total_contradictions = 0
        contradiction_by_severity: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        contradiction_by_type: Dict[str, int] = {}

        if contra_query is not None:
            contra_res = await db.execute(contra_query)
            contradictions = contra_res.scalars().all()
            total_contradictions = len(contradictions)
            for c in contradictions:
                sev = str(c.severity).split(".")[-1].lower()
                if sev in contradiction_by_severity:
                    contradiction_by_severity[sev] += 1
                ctype = str(c.type).lower()
                contradiction_by_type[ctype] = contradiction_by_type.get(ctype, 0) + 1

        # Contradiction rate per finalized evaluation
        contradiction_rate = (
            round((total_contradictions / total_evals), 2)
            if total_evals > 0 else 0.0
        )

        critical_count = contradiction_by_severity.get("critical", 0)

        # Override rate as proxy for grounding override signal
        override_rate = (
            round((override_count / total_comp_scores) * 100.0, 2)
            if total_comp_scores > 0 else 0.0
        )
        insufficient_rate = (
            round((insufficient_count / total_comp_scores) * 100.0, 2)
            if total_comp_scores > 0 else 0.0
        )

        return {
            "sample_size": total_evals,
            "total_competency_scores_analyzed": total_comp_scores,
            "competency_grounding": {
                "human_override_count": override_count,
                "human_override_rate": override_rate,
                "insufficient_evidence_count": insufficient_count,
                "insufficient_evidence_rate": insufficient_rate,
                "note": (
                    "Override rate reflects competencies where human reviewers "
                    "corrected the AI-proposed score. Insufficient evidence rate "
                    "reflects competencies lacking adequate candidate evidence."
                ),
            },
            "contradiction_analytics": {
                "total_contradictions": total_contradictions,
                "contradiction_rate_per_evaluation": contradiction_rate,
                "by_severity": contradiction_by_severity,
                "critical_contradiction_count": critical_count,
                "by_type": contradiction_by_type,
                "terminology_note": (
                    "Contradictions represent conflicting evidence signals, not necessarily "
                    "candidate dishonesty. Each contradiction requires human review."
                ),
            },
        }


ai_telemetry_analytics_service = AITelemetryAnalyticsService()

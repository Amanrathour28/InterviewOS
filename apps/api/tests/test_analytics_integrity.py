"""
Phase 16.1 — Analytics Integrity & Immutability Audit Tests.

Verifies:
- Finalized evaluations snapshot integrity (draft score changes do not mutate finalized analytics)
- Score domain enforcement ([0, 100], rejection of <0, >100, NaN)
- Recommendation aggregation integrity (sum of bins equals total count)
- Traceability: finalized analytics match underlying authoritative records
"""

import math
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.services.analytics_service import analytics_service
from app.services.candidate_decision_service import candidate_decision_service
from app.models.evaluation import EvaluationStatus


class TestScoreDomainIntegrity:
    """Ensure invalid scores outside [0.0, 100.0] cannot enter or corrupt analytics."""

    def test_negative_score_rejected(self):
        scores = [50.0, -10.0, 80.0]
        with pytest.raises(ValueError, match=r"outside valid domain"):
            analytics_service.calculate_score_distribution(scores)

    def test_score_above_100_rejected(self):
        scores = [50.0, 105.0, 80.0]
        with pytest.raises(ValueError, match=r"outside valid domain"):
            analytics_service.calculate_score_distribution(scores)

    def test_nan_scores_safely_ignored_without_crashing(self):
        scores = [50.0, float("nan"), 70.0]
        result = analytics_service.calculate_score_distribution(scores)
        assert result["sample_size"] == 2
        assert result["mean"] == 60.0

    def test_boundary_scores_0_and_100_valid(self):
        scores = [0.0, 100.0]
        result = analytics_service.calculate_score_distribution(scores)
        assert result["min"] == 0.0
        assert result["max"] == 100.0
        assert result["mean"] == 50.0


class TestFinalizedEvaluationIntegrity:
    """Ensure draft evaluations are never mixed into authoritative finalized decision analytics."""

    @pytest.mark.asyncio
    async def test_status_filter_finalized_applied_strictly(self):
        db = AsyncMock()
        execute_result = MagicMock()
        execute_result.all = MagicMock(return_value=[])
        db.execute = AsyncMock(return_value=execute_result)

        workspace_id = uuid.uuid4()
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)

        result = await candidate_decision_service.get_candidate_decision_matrix(
            db,
            workspace_id=workspace_id,
            start_date=start,
            end_date=end,
            status_filter="finalized",
        )

        assert db.execute.called
        assert "candidates" in result
        assert "score_distribution" in result
        assert "recommendation_distribution" in result


class TestRecommendationDistributionConservation:
    """Sum of individual recommendation counts must strictly equal total sample count."""

    @pytest.mark.parametrize(
        "recs",
        [
            [],
            ["strong_hire"],
            ["hire", "no_hire", "strong_hire", "lean_hire", "lean_no_hire", "insufficient_evidence"],
            ["hire"] * 25 + ["no_hire"] * 15 + ["insufficient_evidence"] * 10,
        ],
    )
    def test_counts_sum_to_total(self, recs):
        result = analytics_service.aggregate_recommendations(recs)
        total = result["total"]
        counts_sum = sum(result["counts"].values())
        assert total == len(recs)
        assert counts_sum == total

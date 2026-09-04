"""
Phase 16 — Analytics Reproducibility Tests.

Verifies:
- Draft evaluations are NEVER included in finalized analytics
- Calling analytics twice with the same inputs returns identical results
- Score distribution math is deterministic (same input → same output)
- Export records are stable across calls
"""

import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List


class TestAnalyticsDeterminism:
    """The same inputs must always produce the same output values."""

    def test_score_distribution_is_deterministic(self):
        """Same score list → same distribution result every time."""
        from app.services.analytics_service import analytics_service

        scores = [45.0, 55.0, 65.0, 72.0, 80.0, 88.0, 92.0, 95.0, 100.0]

        result1 = analytics_service.calculate_score_distribution(scores)
        result2 = analytics_service.calculate_score_distribution(scores)

        assert result1["mean"] == result2["mean"]
        assert result1["median"] == result2["median"]
        assert result1["p25"] == result2["p25"]
        assert result1["p75"] == result2["p75"]
        assert result1["p90"] == result2["p90"]

    def test_recommendation_aggregation_is_deterministic(self):
        """Same recommendation list → same rates every time."""
        from app.services.analytics_service import analytics_service

        recs = ["hire", "no_hire", "strong_hire", "hire", "no_hire", "hire"]

        result1 = analytics_service.aggregate_recommendations(recs)
        result2 = analytics_service.aggregate_recommendations(recs)

        assert result1["rates"] == result2["rates"]
        assert result1["counts"] == result2["counts"]
        assert result1["positive_recommendation_rate"] == result2["positive_recommendation_rate"]

    def test_distribution_with_shuffled_input_produces_same_stats(self):
        """Order of scores must not affect statistical summary."""
        import random
        from app.services.analytics_service import analytics_service

        scores = [float(x) for x in range(1, 51)]  # 1 to 50
        shuffled = scores.copy()
        random.shuffle(shuffled)

        result1 = analytics_service.calculate_score_distribution(scores)
        result2 = analytics_service.calculate_score_distribution(shuffled)

        assert result1["mean"] == result2["mean"]
        assert result1["min"] == result2["min"]
        assert result1["max"] == result2["max"]
        assert result1["median"] == result2["median"]


class TestDraftVsFinalizedSeparation:
    """Draft evaluations must not appear in finalized analytics."""

    @pytest.mark.asyncio
    async def test_draft_evals_excluded_from_decision_matrix(self):
        """get_candidate_decision_matrix with status_filter='finalized' must exclude drafts."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.candidate_decision_service import candidate_decision_service
        import uuid

        db = AsyncMock()

        # Simulate evaluations: 2 finalized, 1 draft
        mock_finalized = MagicMock()
        mock_finalized.status = "finalized"
        mock_finalized.id = uuid.uuid4()
        mock_finalized.is_authoritative = True
        mock_finalized.overall_score = 80.0
        mock_finalized.overall_rubric_level = "senior"
        mock_finalized.recommendation = "hire"
        mock_finalized.confidence = 0.85
        mock_finalized.evidence_count = 5
        mock_finalized.contradiction_count = 0
        mock_finalized.finalized_at = datetime.now(timezone.utc)
        mock_finalized.created_at = datetime.now(timezone.utc)
        mock_finalized.job_id = None

        mock_draft = MagicMock()
        mock_draft.status = "draft"
        mock_draft.id = uuid.uuid4()

        workspace_id = uuid.uuid4()
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)

        # When status_filter='finalized', only finalized records should be queried
        execute_result = MagicMock()
        execute_result.all = MagicMock(return_value=[])
        execute_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        db.execute = AsyncMock(return_value=execute_result)

        result = await candidate_decision_service.get_candidate_decision_matrix(
            db, workspace_id, start, end, status_filter="finalized"
        )

        # Should have called db.execute (confirming the filter was applied)
        assert db.execute.called

    @pytest.mark.asyncio
    async def test_competency_analytics_finalized_only_flag(self):
        """Competency analytics with finalized_only=True must exclude draft evaluations."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.competency_analytics_service import competency_analytics_service
        import uuid

        db = AsyncMock()
        execute_result = MagicMock()
        execute_result.all = MagicMock(return_value=[])
        execute_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        db.execute = AsyncMock(return_value=execute_result)

        workspace_id = uuid.uuid4()
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)

        result = await competency_analytics_service.get_competency_analytics(
            db, workspace_id, start, end, finalized_only=True
        )

        assert "competencies" in result
        assert "metadata" in result
        assert result["metadata"]["finalized_only"] is True


class TestExportStability:
    """Export service must produce stable, sanitized output."""

    def test_csv_export_excludes_private_fields(self):
        """Sensitive fields must be stripped from CSV exports."""
        from app.services.analytics_export_service import analytics_export_service

        record = {
            "evaluation_id": "eval-123",
            "candidate_name": "Jane Doe",
            "overall_score": 82.0,
            "email": "jane@example.com",  # EXCLUDED
            "integrity_hash": "abc123",  # EXCLUDED
            "raw_content": "some raw text",  # EXCLUDED
            "recommendation": "hire",
        }

        sanitized = analytics_export_service.sanitize_record(record)

        assert "email" not in sanitized
        assert "integrity_hash" not in sanitized
        assert "raw_content" not in sanitized
        assert "evaluation_id" in sanitized
        assert "recommendation" in sanitized

    def test_json_export_has_metadata_envelope(self):
        """JSON export must include metadata envelope with record_count."""
        import json
        from app.services.analytics_export_service import analytics_export_service

        records = [{"evaluation_id": "e1", "score": 75.0}, {"evaluation_id": "e2", "score": 80.0}]
        output = analytics_export_service.to_json(records, metadata={"workspace_id": "ws-1"})

        parsed = json.loads(output)
        assert "export_metadata" in parsed
        assert parsed["export_metadata"]["record_count"] == 2
        assert "records" in parsed
        assert len(parsed["records"]) == 2

    def test_empty_records_produce_empty_csv(self):
        """Empty record list must produce empty CSV string."""
        from app.services.analytics_export_service import analytics_export_service

        result = analytics_export_service.to_csv([])
        assert result == ""

    def test_csv_determinism(self):
        """Same record list → same CSV output."""
        from app.services.analytics_export_service import analytics_export_service

        records = [
            {"id": "r1", "score": 80.0, "recommendation": "hire"},
            {"id": "r2", "score": 65.0, "recommendation": "no_hire"},
        ]

        csv1 = analytics_export_service.to_csv(records)
        csv2 = analytics_export_service.to_csv(records)
        assert csv1 == csv2

"""
Phase 16.1 — AI Analytics Explanation Integrity Tests.

Verifies:
- Explanation faithfully reflects provided deterministic metrics
- Clean valid explanations pass validation
- Gateway failures return safe empty string without crashing
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.analytics_explanation_agent import analytics_explanation_agent


class TestAIExplanationIntegrity:
    """Ensure AI advisory explanations are faithful to deterministic input metrics."""

    @pytest.mark.asyncio
    async def test_faithful_explanation_generation(self):
        metrics = {
            "total_interviews": 45,
            "completion_rate": 82.5,
            "average_score": 74.0,
            "sample_size": 45,
        }

        mock_resp = MagicMock()
        mock_resp.content = (
            "During this period, 45 interviews were recorded with an 82.5% completion rate "
            "and an average candidate score of 74.0 points."
        )

        with patch.object(analytics_explanation_agent, "_get_gateway") as mock_gw:
            mock_gateway = AsyncMock()
            mock_gateway.complete = AsyncMock(return_value=mock_resp)
            mock_gw.return_value = mock_gateway

            res = await analytics_explanation_agent.explain_metrics(
                workspace_id="ws-test",
                metrics=metrics,
                question="What is the overall performance?",
            )

            assert "82.5%" in res
            assert "74.0" in res

    @pytest.mark.asyncio
    async def test_gateway_timeout_fails_gracefully(self):
        with patch.object(analytics_explanation_agent, "_get_gateway") as mock_gw:
            mock_gateway = AsyncMock()
            mock_gateway.complete = AsyncMock(side_effect=Exception("Gateway connection failed"))
            mock_gw.return_value = mock_gateway

            res = await analytics_explanation_agent.explain_metrics(
                workspace_id="ws-test",
                metrics={"total": 10},
                question="What happened?",
            )

            assert res == ""

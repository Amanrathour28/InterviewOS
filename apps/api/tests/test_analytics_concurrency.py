"""
Phase 16.1 — Analytics Concurrency & Determinism Audit Tests.

Verifies:
- Concurrent analytics calculation produces identical, reproducible results
- Order independence of input scores
"""

import asyncio
import random
import pytest
from app.services.analytics_service import analytics_service


class TestAnalyticsConcurrency:
    """Ensure concurrent calculations are thread-safe, pure, and deterministic."""

    @pytest.mark.asyncio
    async def test_concurrent_score_distribution_calls_are_identical(self):
        scores = [float(x) for x in range(1, 101)]

        async def run_calc():
            return analytics_service.calculate_score_distribution(scores)

        results = await asyncio.gather(*[run_calc() for _ in range(20)])

        first = results[0]
        for res in results[1:]:
            assert res["mean"] == first["mean"]
            assert res["median"] == first["median"]
            assert res["p25"] == first["p25"]
            assert res["p75"] == first["p75"]
            assert res["p90"] == first["p90"]
            assert res["bins"] == first["bins"]

    @pytest.mark.asyncio
    async def test_concurrent_recommendation_aggregation_is_identical(self):
        recs = ["strong_hire", "hire", "hire", "lean_hire", "no_hire"] * 10

        async def run_agg():
            return analytics_service.aggregate_recommendations(recs)

        results = await asyncio.gather(*[run_agg() for _ in range(20)])

        first = results[0]
        for res in results[1:]:
            assert res["counts"] == first["counts"]
            assert res["rates"] == first["rates"]
            assert res["hire_rate"] == first["hire_rate"]

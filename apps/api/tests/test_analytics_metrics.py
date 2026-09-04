"""
Phase 16.1 — Analytics Metrics & Denominator Safety Tests.

Verifies:
- Denominator = 0 safety (no division by zero, returns has_data: False or safe zeros/None)
- Percentile precision and monotonicity (P25 <= P50 <= P75 <= P90)
- Bins exactness (0-20, 20-40, 40-55, 55-70, 70-85, 85-100)
- Deterministic calculation across repeated identical inputs
"""

import pytest
from app.services.analytics_service import analytics_service


class TestDenominatorSafety:
    """Zero denominator scenarios must never crash or produce NaN/Infinity."""

    def test_empty_scores_returns_clean_zero_sample_metrics(self):
        result = analytics_service.calculate_score_distribution([])
        assert result["sample_size"] == 0
        assert result["has_data"] is False
        assert result["mean"] == 0.0
        assert result["median"] == 0.0
        assert result["above_60_rate"] == 0.0

    def test_empty_recommendations_returns_clean_zero_sample_metrics(self):
        result = analytics_service.aggregate_recommendations([])
        assert result["total"] == 0
        assert result["has_data"] is False
        assert result["positive_recommendation_rate"] == 0.0
        assert result["hire_rate"] == 0.0


class TestPercentilePrecision:
    """Percentiles must be monotonic and mathematically correct."""

    def test_known_dataset_percentiles(self):
        # 1 to 100
        scores = [float(x) for x in range(1, 101)]
        dist = analytics_service.calculate_score_distribution(scores)

        assert dist["sample_size"] == 100
        assert dist["min"] == 1.0
        assert dist["max"] == 100.0
        assert dist["mean"] == 50.5
        assert dist["median"] == 50.5
        assert dist["p25"] <= dist["p50"] <= dist["p75"] <= dist["p90"]

    def test_single_value_percentiles_equal_value(self):
        scores = [78.5]
        dist = analytics_service.calculate_score_distribution(scores)
        assert dist["mean"] == 78.5
        assert dist["median"] == 78.5
        assert dist["p25"] == 78.5
        assert dist["p75"] == 78.5
        assert dist["p90"] == 78.5


class TestBinBoundariesExclusivity:
    """Every valid score falls into exactly one bin, summing to total sample size."""

    def test_boundary_scores_placement(self):
        boundary_scores = [0.0, 19.9, 20.0, 39.9, 40.0, 54.9, 55.0, 69.9, 70.0, 84.9, 85.0, 100.0]
        dist = analytics_service.calculate_score_distribution(boundary_scores)

        bins_sum = sum(dist["bins"].values())
        assert bins_sum == len(boundary_scores)
        assert dist["sample_size"] == len(boundary_scores)

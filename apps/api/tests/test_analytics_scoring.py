"""
Phase 16 — Analytics Scoring Formula Unit Tests.

Tests deterministic math utilities: score distributions, recommendation aggregation,
percentile calculations, and time window parsing.
"""

import math
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from app.services.analytics_service import analytics_service


class TestScoreDistributionCalculation:

    def test_empty_input_returns_zero_defaults(self):
        result = analytics_service.calculate_score_distribution([])
        assert result["mean"] == 0.0
        assert result["median"] == 0.0
        assert result["min"] == 0.0
        assert result["max"] == 0.0
        assert result["sample_size"] == 0

    def test_single_value_distribution(self):
        result = analytics_service.calculate_score_distribution([75.0])
        assert result["mean"] == 75.0
        assert result["median"] == 75.0
        assert result["min"] == 75.0
        assert result["max"] == 75.0

    def test_uniform_distribution(self):
        scores = [50.0, 60.0, 70.0, 80.0, 90.0]
        result = analytics_service.calculate_score_distribution(scores)
        assert result["mean"] == 70.0
        assert result["median"] == 70.0
        assert result["min"] == 50.0
        assert result["max"] == 90.0

    def test_distribution_sample_size(self):
        scores = [float(x) for x in range(100)]
        result = analytics_service.calculate_score_distribution(scores)
        assert result["sample_size"] == 100

    def test_percentile_ordering(self):
        scores = [float(x) for x in range(1, 101)]  # 1 to 100
        result = analytics_service.calculate_score_distribution(scores)
        # p25, p75, p90 must be ordered
        assert result["p25"] <= result["p75"]
        assert result["p75"] <= result["p90"]

    def test_distribution_buckets_sum_to_total_percentage(self):
        scores = [10.0, 20.0, 35.0, 50.0, 65.0, 80.0, 95.0]
        result = analytics_service.calculate_score_distribution(scores)
        bucket_total = sum(result["distribution_buckets"].values())
        # Each bucket is a count; total should sum to sample size
        assert bucket_total == len(scores)

    def test_above_threshold_rate(self):
        scores = [60.0, 70.0, 80.0, 40.0, 50.0]
        result = analytics_service.calculate_score_distribution(scores)
        # 3 scores >= 60
        assert result["above_60_rate"] == pytest.approx(60.0, abs=0.1)


class TestRecommendationAggregation:

    def test_empty_recommendations(self):
        result = analytics_service.aggregate_recommendations([])
        assert result["total"] == 0
        for val in result["counts"].values():
            assert val == 0

    def test_recommendation_counts_match_total(self):
        recs = ["strong_hire", "hire", "no_hire", "strong_hire", "hire"]
        result = analytics_service.aggregate_recommendations(recs)
        assert result["total"] == 5
        assert result["counts"]["strong_hire"] == 2
        assert result["counts"]["hire"] == 2
        assert result["counts"]["no_hire"] == 1

    def test_rate_calculation(self):
        recs = ["hire", "hire", "no_hire", "no_hire"]
        result = analytics_service.aggregate_recommendations(recs)
        assert result["rates"]["hire"] == pytest.approx(50.0, abs=0.1)
        assert result["rates"]["no_hire"] == pytest.approx(50.0, abs=0.1)

    def test_positive_recommendation_rate(self):
        recs = ["strong_hire", "hire", "hire", "no_hire"]
        result = analytics_service.aggregate_recommendations(recs)
        # strong_hire + hire = 3, total = 4 → 75%
        assert result["positive_recommendation_rate"] == pytest.approx(75.0, abs=0.1)


class TestTimeWindowParsing:

    def test_7d_window(self):
        start, end = analytics_service.parse_time_window(window="7d")
        diff = (end - start).days
        assert diff == 7

    def test_30d_window(self):
        start, end = analytics_service.parse_time_window(window="30d")
        diff = (end - start).days
        assert diff == 30

    def test_90d_window(self):
        start, end = analytics_service.parse_time_window(window="90d")
        diff = (end - start).days
        assert diff == 90

    def test_365d_window(self):
        start, end = analytics_service.parse_time_window(window="365d")
        diff = (end - start).days
        assert diff == 365

    def test_custom_dates_override_window(self):
        custom_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        custom_end = datetime(2025, 6, 30, tzinfo=timezone.utc)
        start, end = analytics_service.parse_time_window(
            window="7d",  # should be ignored
            from_date=custom_start,
            to_date=custom_end,
        )
        assert start == custom_start
        assert end == custom_end

    def test_end_is_always_utc(self):
        start, end = analytics_service.parse_time_window(window="30d")
        assert end.tzinfo is not None

    def test_unknown_window_defaults_to_30d(self):
        start, end = analytics_service.parse_time_window(window="invalid_window")
        diff = (end - start).days
        assert diff == 30


class TestPercentileCalculation:

    def test_p50_equals_median(self):
        scores = [float(x) for x in range(1, 101)]
        result = analytics_service.calculate_score_distribution(scores)
        assert abs(result["p50"] - result["median"]) < 1.0

    def test_all_same_scores(self):
        scores = [75.0] * 50
        result = analytics_service.calculate_score_distribution(scores)
        assert result["mean"] == 75.0
        assert result["p25"] == 75.0
        assert result["p75"] == 75.0

    def test_two_values_distribution(self):
        result = analytics_service.calculate_score_distribution([0.0, 100.0])
        assert result["min"] == 0.0
        assert result["max"] == 100.0
        assert result["mean"] == 50.0

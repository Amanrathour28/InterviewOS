"""
Phase 16 — Analytics Core Utility Service.

Provides:
- Deterministic time-window parsing (today, 7d, 30d, 90d, this_quarter, previous_quarter, custom)
- Score distribution calculation & percentile computation
- Recommendation aggregation
- Tenant-scoped caching utilities
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger("interviewos.api.analytics_service")


class AnalyticsService:
    """Core analytics calculation and normalization utility."""

    @staticmethod
    def parse_time_window(
        window: str = "30d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Tuple[datetime, datetime]:
        """
        Parses standard time windows into UTC datetime boundaries [start_utc, end_utc].
        Custom from_date/to_date explicitly override the window boundaries.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=30)
        end = now

        if window == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif window == "this_quarter":
            quarter = (now.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start = datetime(now.year, start_month, 1, tzinfo=timezone.utc)
            end = now
        elif window == "previous_quarter":
            quarter = (now.month - 1) // 3 + 1
            prev_quarter = quarter - 1 if quarter > 1 else 4
            prev_year = now.year if quarter > 1 else now.year - 1
            start_month = (prev_quarter - 1) * 3 + 1
            end_month = start_month + 3
            start = datetime(prev_year, start_month, 1, tzinfo=timezone.utc)
            if end_month > 12:
                end = datetime(prev_year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(microseconds=1)
            else:
                end = datetime(prev_year, end_month, 1, tzinfo=timezone.utc) - timedelta(microseconds=1)
        elif window and window.endswith("d") and window[:-1].isdigit():
            days = int(window[:-1])
            start = now - timedelta(days=days)
            end = now

        if from_date is not None:
            start = from_date if from_date.tzinfo else from_date.replace(tzinfo=timezone.utc)
        if to_date is not None:
            end = to_date if to_date.tzinfo else to_date.replace(tzinfo=timezone.utc)

        return start, end

    @staticmethod
    def calculate_score_distribution(scores: List[float]) -> Dict[str, Any]:
        """
        Computes deterministic score distribution bins and summary statistics.
        Bins: 0-20, 20-40, 40-55, 55-70, 70-85, 85-100.
        """
        # Validate scores domain
        cleaned_scores: List[float] = []
        for s in scores:
            if s is None or math.isnan(s):
                continue
            if s < 0.0 or s > 100.0:
                raise ValueError(f"Score {s} outside valid domain [0.0, 100.0]")
            cleaned_scores.append(float(s))

        if not cleaned_scores:
            return {
                "sample_size": 0,
                "has_data": False,
                "mean": 0.0,
                "median": 0.0,
                "p50": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std_dev": 0.0,
                "p25": 0.0,
                "p75": 0.0,
                "p90": 0.0,
                "above_60_rate": 0.0,
                "distribution_buckets": {
                    "0_20": 0,
                    "20_40": 0,
                    "40_55": 0,
                    "55_70": 0,
                    "70_85": 0,
                    "85_100": 0,
                },
                "bins": {
                    "0_20": 0,
                    "20_40": 0,
                    "40_55": 0,
                    "55_70": 0,
                    "70_85": 0,
                    "85_100": 0,
                },
                "bin_percentages": {
                    "0_20": 0.0,
                    "20_40": 0.0,
                    "40_55": 0.0,
                    "55_70": 0.0,
                    "70_85": 0.0,
                    "85_100": 0.0,
                },
            }

        sorted_scores = sorted(cleaned_scores)
        n = len(sorted_scores)
        mean_score = sum(sorted_scores) / n

        # Median
        if n % 2 == 1:
            median_score = sorted_scores[n // 2]
        else:
            median_score = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2.0

        # Variance & Std Dev
        variance = sum((s - mean_score) ** 2 for s in sorted_scores) / n
        std_dev = math.sqrt(variance)

        # Percentile helper (deterministic linear interpolation)
        def percentile(p: float) -> float:
            k = (n - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_scores[int(k)]
            return sorted_scores[int(f)] * (c - k) + sorted_scores[int(c)] * (k - f)

        bins = {
            "0_20": 0,
            "20_40": 0,
            "40_55": 0,
            "55_70": 0,
            "70_85": 0,
            "85_100": 0,
        }

        above_60_count = 0
        for s in sorted_scores:
            if s >= 60.0:
                above_60_count += 1
            if s < 20.0:
                bins["0_20"] += 1
            elif s < 40.0:
                bins["20_40"] += 1
            elif s < 55.0:
                bins["40_55"] += 1
            elif s < 70.0:
                bins["55_70"] += 1
            elif s < 85.0:
                bins["70_85"] += 1
            else:
                bins["85_100"] += 1

        bin_percentages = {
            k: round((count / n) * 100.0, 2) for k, count in bins.items()
        }

        above_60_rate = round((above_60_count / n) * 100.0, 2)

        return {
            "sample_size": n,
            "has_data": True,
            "mean": round(mean_score, 2),
            "median": round(median_score, 2),
            "p50": round(median_score, 2),
            "min": round(sorted_scores[0], 2),
            "max": round(sorted_scores[-1], 2),
            "std_dev": round(std_dev, 2),
            "p25": round(percentile(0.25), 2),
            "p75": round(percentile(0.75), 2),
            "p90": round(percentile(0.90), 2),
            "above_60_rate": above_60_rate,
            "distribution_buckets": bins,
            "bins": bins,
            "bin_percentages": bin_percentages,
        }

    @staticmethod
    def aggregate_recommendations(recommendations: List[str]) -> Dict[str, Any]:
        """
        Aggregates recommendation counts and rates from list of recommendation strings.
        """
        canonical_keys = [
            "strong_hire",
            "hire",
            "lean_hire",
            "lean_no_hire",
            "no_hire",
            "insufficient_evidence",
        ]
        counts = {k: 0 for k in canonical_keys}

        for rec in recommendations:
            key = str(rec).lower()
            if key in counts:
                counts[key] += 1
            else:
                counts["insufficient_evidence"] += 1

        total = len(recommendations)
        rates = {
            k: round((count / total) * 100.0, 2) if total > 0 else 0.0
            for k, count in counts.items()
        }

        positive_count = counts["strong_hire"] + counts["hire"]
        positive_rate = round((positive_count / total) * 100.0, 2) if total > 0 else 0.0
        hire_count = counts["strong_hire"] + counts["hire"] + counts["lean_hire"]
        hire_rate = round((hire_count / total) * 100.0, 2) if total > 0 else 0.0

        return {
            "total": total,
            "has_data": total > 0,
            "counts": counts,
            "percentages": rates,
            "rates": rates,
            "positive_recommendation_rate": positive_rate,
            "hire_rate": hire_rate,
        }

    @staticmethod
    def calculate_recommendation_distribution(recommendations: List[str]) -> Dict[str, Any]:
        """Alias for aggregate_recommendations."""
        return AnalyticsService.aggregate_recommendations(recommendations)

    @staticmethod
    def build_cache_key(workspace_id: uuid.UUID, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Builds a strictly tenant-isolated, deterministic Redis cache key.
        """
        clean_params = params or {}
        serialized = json.dumps(clean_params, sort_keys=True, default=str)
        param_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"analytics:{workspace_id}:{endpoint}:{param_hash}"


analytics_service = AnalyticsService()

"""
Phase 16 — Analytics Filter Tests.

Tests date filter parsing, time window edge cases, unknown filters,
and filter combination scenarios.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.services.analytics_service import analytics_service


class TestDateWindowParsing:
    """Test all time window string variants and custom date range overrides."""

    VALID_WINDOWS = [
        ("7d", 7),
        ("14d", 14),
        ("30d", 30),
        ("60d", 60),
        ("90d", 90),
        ("180d", 180),
        ("365d", 365),
    ]

    @pytest.mark.parametrize("window,expected_days", VALID_WINDOWS)
    def test_valid_window_produces_correct_day_span(self, window: str, expected_days: int):
        start, end = analytics_service.parse_time_window(window=window)
        diff = (end - start).days
        assert diff == expected_days, f"Window {window} should produce {expected_days} days, got {diff}"

    def test_unknown_window_defaults_to_30_days(self):
        start, end = analytics_service.parse_time_window(window="xyz")
        diff = (end - start).days
        assert diff == 30

    def test_empty_window_string_defaults_to_30_days(self):
        start, end = analytics_service.parse_time_window(window="")
        diff = (end - start).days
        assert diff == 30

    def test_custom_from_date_overrides_window(self):
        custom_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        start, end = analytics_service.parse_time_window(
            window="90d", from_date=custom_start
        )
        assert start == custom_start

    def test_custom_to_date_overrides_window(self):
        custom_end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        start, end = analytics_service.parse_time_window(
            window="90d", to_date=custom_end
        )
        assert end == custom_end

    def test_both_custom_dates_override_window_completely(self):
        custom_start = datetime(2024, 6, 1, tzinfo=timezone.utc)
        custom_end = datetime(2024, 9, 1, tzinfo=timezone.utc)
        start, end = analytics_service.parse_time_window(
            window="7d",
            from_date=custom_start,
            to_date=custom_end,
        )
        assert start == custom_start
        assert end == custom_end

    def test_start_is_before_end(self):
        start, end = analytics_service.parse_time_window(window="30d")
        assert start < end

    def test_end_is_not_in_future_by_more_than_one_minute(self):
        """Confirm end time is approximately 'now' (not some far future date)."""
        start, end = analytics_service.parse_time_window(window="30d")
        now = datetime.now(timezone.utc)
        # end should be within 60 seconds of now
        diff = abs((end - now).total_seconds())
        assert diff < 60


class TestDateFilterEdgeCases:
    """Edge cases for date filter inputs."""

    def test_naive_datetime_is_handled(self):
        """Naive datetime (no tzinfo) should be handled without crash."""
        naive_start = datetime(2025, 1, 1)  # No timezone
        try:
            start, end = analytics_service.parse_time_window(
                window="30d",
                from_date=naive_start,
            )
            # If no crash, the function handles it
            assert start is not None
        except Exception as exc:
            pytest.fail(f"parse_time_window raised with naive datetime: {exc}")

    def test_reversed_dates_do_not_crash(self):
        """When from_date > to_date, function should not crash (result may be inconsistent)."""
        future = datetime(2030, 1, 1, tzinfo=timezone.utc)
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        try:
            analytics_service.parse_time_window(
                window="30d", from_date=future, to_date=past
            )
        except Exception as exc:
            pytest.fail(f"parse_time_window raised with reversed dates: {exc}")

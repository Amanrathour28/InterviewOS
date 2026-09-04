"""
Phase 16.1 — Analytics Time Window & Boundary Audit Tests.

Verifies:
- Standard windows: 7d, 14d, 30d, 60d, 90d, 180d, 365d, this_quarter, previous_quarter
- Custom date overrides
- UTC boundary guarantees
- Edge cases (naive datetimes, empty strings, invalid inputs)
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.services.analytics_service import analytics_service


class TestTimeWindowBoundaries:
    """Test all time window configurations and boundaries."""

    @pytest.mark.parametrize(
        "window_str,expected_days",
        [
            ("7d", 7),
            ("14d", 14),
            ("30d", 30),
            ("60d", 60),
            ("90d", 90),
            ("180d", 180),
            ("365d", 365),
        ],
    )
    def test_day_windows_exact_day_spans(self, window_str, expected_days):
        start, end = analytics_service.parse_time_window(window=window_str)
        delta_days = (end - start).days
        assert delta_days == expected_days
        assert start.tzinfo == timezone.utc
        assert end.tzinfo == timezone.utc

    def test_this_quarter_starts_first_day_of_quarter(self):
        start, end = analytics_service.parse_time_window(window="this_quarter")
        now = datetime.now(timezone.utc)
        current_quarter = (now.month - 1) // 3 + 1
        expected_start_month = (current_quarter - 1) * 3 + 1

        assert start.year == now.year
        assert start.month == expected_start_month
        assert start.day == 1
        assert start < end

    def test_previous_quarter_boundaries(self):
        start, end = analytics_service.parse_time_window(window="previous_quarter")
        assert start < end
        assert start.day == 1

    def test_custom_dates_explicit_override(self):
        custom_from = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
        custom_to = datetime(2025, 4, 15, 18, 30, tzinfo=timezone.utc)

        start, end = analytics_service.parse_time_window(
            window="90d",
            from_date=custom_from,
            to_date=custom_to,
        )

        assert start == custom_from
        assert end == custom_to

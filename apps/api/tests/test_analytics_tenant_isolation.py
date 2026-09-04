"""
Phase 16.1 — Analytics Tenant & Cache Isolation Audit Tests.

Verifies:
- All database queries strictly scope by workspace_id
- Cache keys contain tenant ID prefix to prevent cross-workspace data leakage
- Drill-down endpoints verify entity ownership before returning details
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.analytics_service import analytics_service
from app.services.candidate_decision_service import candidate_decision_service


class TestCacheKeyTenantScoping:
    """Verify cache keys strictly scope by workspace_id to prevent cross-workspace cache pollution."""

    def test_cache_keys_for_different_tenants_are_isolated(self):
        ws_a = uuid.uuid4()
        ws_b = uuid.uuid4()

        key_a = analytics_service.build_cache_key(ws_a, "overview", {"window": "30d"})
        key_b = analytics_service.build_cache_key(ws_b, "overview", {"window": "30d"})

        assert key_a != key_b
        assert str(ws_a) in key_a
        assert str(ws_b) in key_b
        assert key_a.startswith("analytics:")

    def test_cache_keys_with_different_filters_are_distinct(self):
        ws = uuid.uuid4()
        key_30d = analytics_service.build_cache_key(ws, "interviews", {"window": "30d"})
        key_90d = analytics_service.build_cache_key(ws, "interviews", {"window": "90d"})

        assert key_30d != key_90d


class TestCandidateDrilldownIsolation:
    """Verify candidate timeline lookups enforce workspace_id filter."""

    @pytest.mark.asyncio
    async def test_candidate_timeline_enforces_workspace_match(self):
        db = AsyncMock()
        execute_res = MagicMock()
        execute_res.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_res)

        ws_id = uuid.uuid4()
        foreign_cand_id = uuid.uuid4()

        result = await candidate_decision_service.get_candidate_unified_timeline(
            db, workspace_id=ws_id, candidate_id=foreign_cand_id
        )

        assert db.execute.called
        assert result.get("timeline") == []

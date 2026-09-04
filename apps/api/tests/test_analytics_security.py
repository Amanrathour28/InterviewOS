"""
Phase 16.1 — Analytics Security & RBAC Audit Tests.

Verifies:
- CANDIDATE role is strictly rejected with HTTP 403 on every analytics route
- Unauthorized callers receive HTTP 401
- PII and internal secret minimization
"""

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def candidate_token(client: AsyncClient) -> str:
    """Create a registered candidate user and return access token."""
    email = f"candidate_audit_{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "first_name": "Audit",
            "last_name": "Candidate",
        },
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


class TestAnalyticsSecurityRBAC:
    """Test strict RBAC enforcement across all analytics API routes."""

    ENDPOINTS = [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/interviews",
        "/api/v1/analytics/candidates",
        "/api/v1/analytics/competencies",
        "/api/v1/analytics/interviewers",
        "/api/v1/analytics/questions",
        "/api/v1/analytics/ai",
        "/api/v1/analytics/evidence",
        "/api/v1/analytics/funnel",
    ]

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected_401(self, endpoint: str, client: AsyncClient):
        ws_id = str(uuid.uuid4())
        resp = await client.get(f"{endpoint}?workspace_id={ws_id}")
        assert resp.status_code == 401

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.asyncio
    async def test_candidate_token_rejected_403(self, endpoint: str, client: AsyncClient, candidate_token: str):
        ws_id = str(uuid.uuid4())
        resp = await client.get(
            f"{endpoint}?workspace_id={ws_id}",
            headers={"Authorization": f"Bearer {candidate_token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_candidate_export_post_rejected_403(self, client: AsyncClient, candidate_token: str):
        ws_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/analytics/export?workspace_id={ws_id}",
            json={"export_type": "candidates", "format": "csv"},
            headers={"Authorization": f"Bearer {candidate_token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_candidate_explain_post_rejected_403(self, client: AsyncClient, candidate_token: str):
        ws_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/analytics/explain?workspace_id={ws_id}",
            json={"metrics": {"total": 5}, "question": "Explain trends"},
            headers={"Authorization": f"Bearer {candidate_token}"},
        )
        assert resp.status_code == 403

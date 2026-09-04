import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ai_health_endpoint_requires_auth(client: AsyncClient):
    # Unauthenticated request returns 401
    res = await client.get("/api/v1/ai/health")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_ai_health_endpoint_authenticated(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"ai.health.{uid}@example.com", "password": "Password123!", "first_name": "AI", "last_name": "Tester"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    res = await client.get("/api/v1/ai/health", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_ai_endpoints_reject_invalid_uuid(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"ai.invalid.{uid}@example.com", "password": "Password123!", "first_name": "AI", "last_name": "Tester"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    res = await client.post(
        "/api/v1/ai/generate-question",
        headers=headers,
        json={
            "interview_id": "not-a-valid-uuid",
            "workspace_id": "not-a-valid-uuid",
            "difficulty": "medium",
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_ai_logs_isolation(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"ai.logs.{uid}@example.com", "password": "Password123!", "first_name": "AI", "last_name": "Tester"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": f"AIOrg-{uid}", "initial_workspace_name": "AI-WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Logs for workspace where user is a member
    res = await client.get(f"/api/v1/ai/logs?workspace_id={ws_id}", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Logs for another random workspace should return 403 / 404
    random_ws = str(uuid.uuid4())
    res_forbidden = await client.get(f"/api/v1/ai/logs?workspace_id={random_ws}", headers=headers)
    assert res_forbidden.status_code in (403, 404)

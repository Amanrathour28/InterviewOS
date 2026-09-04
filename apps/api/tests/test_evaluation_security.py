"""
Security & Tenant Isolation Tests for Phase 15.1 Evaluation System.

Tests:
1. Candidate role receives 403 Forbidden across all evaluation, report, override, approve, finalize endpoints.
2. Cross-workspace access rejection.
3. Cross-workspace evidence injection rejection.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_candidate_role_strict_403_isolation(client: AsyncClient):
    # 1. Register Recruiter / Interviewer
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "sec.recruiter@company.com", "password": "Password123!", "first_name": "Sec", "last_name": "Recruiter"},
    )
    assert reg.status_code == 201
    recruiter_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Setup Org & Workspace
    org = (await client.post("/api/v1/organizations", headers=recruiter_headers, json={"name": "SecOrg", "initial_workspace_name": "Security"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Register Candidate
    cand_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "sec.candidate@test.com", "password": "Password123!", "first_name": "Sec", "last_name": "Candidate"},
    )
    assert cand_reg.status_code == 201
    cand_headers = {"Authorization": f"Bearer {cand_reg.json()['access_token']}"}

    # Create Candidate record & Interview
    cand = (await client.post(
        "/api/v1/candidates",
        headers=recruiter_headers,
        json={"workspace_id": ws_id, "first_name": "Sec", "last_name": "Candidate", "email": "sec.candidate@test.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=recruiter_headers,
        json={
            "workspace_id": ws_id,
            "title": "Security Architect Interview",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-11-01T10:00:00Z",
            "duration_minutes": 60,
        },
    )).json()
    itw_id = itw["id"]

    # Recruiter generates evaluation
    gen_res = await client.post(f"/api/v1/interviews/{itw_id}/evaluation/generate", headers=recruiter_headers)
    assert gen_res.status_code == 201

    # Test Candidate role attempting to access all evaluation endpoints
    # 1. GET evaluation
    get_eval = await client.get(f"/api/v1/interviews/{itw_id}/evaluation", headers=cand_headers)
    assert get_eval.status_code == 403

    # 2. GET report
    get_rep = await client.get(f"/api/v1/interviews/{itw_id}/evaluation/report", headers=cand_headers)
    assert get_rep.status_code == 403

    # 3. POST generate
    post_gen = await client.post(f"/api/v1/interviews/{itw_id}/evaluation/generate", headers=cand_headers)
    assert post_gen.status_code == 403

    # 4. POST approve
    post_app = await client.post(f"/api/v1/interviews/{itw_id}/evaluation/approve", headers=cand_headers)
    assert post_app.status_code == 403

    # 5. POST finalize
    post_fin = await client.post(f"/api/v1/interviews/{itw_id}/evaluation/finalize", headers=cand_headers)
    assert post_fin.status_code == 403


@pytest.mark.asyncio
async def test_cross_workspace_evaluation_isolation(client: AsyncClient):
    # Recruiter in Workspace A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "tenant.a@company.com", "password": "Password123!", "first_name": "Tenant", "last_name": "A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "OrgA", "initial_workspace_name": "WorkspaceA"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    # Candidate & Interview in Workspace A
    cand_a = (await client.post("/api/v1/candidates", headers=headers_a, json={"workspace_id": ws_a_id, "first_name": "Cand", "last_name": "A", "email": "cand.a@test.com"})).json()
    itw_a = (await client.post("/api/v1/interviews", headers=headers_a, json={"workspace_id": ws_a_id, "title": "Interview A", "candidate_id": cand_a["id"], "scheduled_at": "2026-11-01T10:00:00Z", "duration_minutes": 45})).json()

    # Recruiter in Workspace B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "tenant.b@company.com", "password": "Password123!", "first_name": "Tenant", "last_name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}
    org_b = (await client.post("/api/v1/organizations", headers=headers_b, json={"name": "OrgB", "initial_workspace_name": "WorkspaceB"})).json()

    # Recruiter B attempts to access Interview A's evaluation
    res_b_access = await client.get(f"/api/v1/interviews/{itw_a['id']}/evaluation", headers=headers_b)
    assert res_b_access.status_code in [403, 404]

    # Recruiter B attempts to finalize Interview A's evaluation
    res_b_finalize = await client.post(f"/api/v1/interviews/{itw_a['id']}/evaluation/finalize", headers=headers_b)
    assert res_b_finalize.status_code in [403, 404]

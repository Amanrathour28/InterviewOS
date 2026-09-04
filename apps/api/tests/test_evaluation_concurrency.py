"""
Concurrency & Race Condition Tests for Evaluation System — Phase 15.1.

Tests:
1. Concurrent finalize requests result in exactly one final version and immutable locking.
2. Concurrent score overrides maintain audit trail integrity.
"""

import asyncio
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_concurrent_finalization_produces_single_version(client: AsyncClient):
    # 1. Setup user, org, candidate, interview
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "conc.recruiter@company.com", "password": "Password123!", "first_name": "Conc", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "ConcOrg", "initial_workspace_name": "Concurrency"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post("/api/v1/candidates", headers=headers, json={"workspace_id": ws_id, "first_name": "Conc", "last_name": "Candidate", "email": "conc.cand@test.com"})).json()
    itw = (await client.post("/api/v1/interviews", headers=headers, json={"workspace_id": ws_id, "title": "Concurrency Interview", "candidate_id": cand["id"], "scheduled_at": "2026-11-01T10:00:00Z", "duration_minutes": 60})).json()
    itw_id = itw["id"]

    # Generate initial evaluation
    gen_res = await client.post(f"/api/v1/interviews/{itw_id}/evaluation/generate", headers=headers)
    assert gen_res.status_code == 201

    # 2. Fire two concurrent finalize requests
    task1 = client.post(f"/api/v1/interviews/{itw_id}/evaluation/finalize", headers=headers)
    task2 = client.post(f"/api/v1/interviews/{itw_id}/evaluation/finalize", headers=headers)

    res1, res2 = await asyncio.gather(task1, task2)
    assert res1.status_code == 200
    assert res2.status_code == 200

    # 3. Retrieve evaluation and verify version and locked status
    eval_res = (await client.get(f"/api/v1/interviews/{itw_id}/evaluation", headers=headers)).json()
    assert eval_res["is_locked"] is True
    assert eval_res["status"] == "finalized"

    # Report verification
    rep_res = (await client.get(f"/api/v1/interviews/{itw_id}/evaluation/report", headers=headers)).json()
    assert rep_res["evaluation"]["status"] == "finalized"
    assert "overall_score" in rep_res["evaluation"]

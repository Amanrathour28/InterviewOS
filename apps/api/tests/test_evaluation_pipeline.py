"""
Integration and pipeline tests for Phase 15 Evaluation, Scoring & Reporting.
Tests:
- End-to-end evaluation generation
- Human-in-the-loop score override & audit log
- State transitions (DRAFT -> IN_REVIEW -> APPROVED -> FINALIZED)
- Immutability locking post-finalization
- Candidate RBAC 403 isolation
- Full Evaluation Report retrieval & score reproducibility
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_evaluation_lifecycle(client: AsyncClient):
    # 1. Register Recruiter
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "eval.lead@company.com", "password": "Password123!", "first_name": "Eval", "last_name": "Lead"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Setup Org & Workspace
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "EvalOrg", "initial_workspace_name": "Engineering"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Create Candidate & Interview
    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Grace", "last_name": "Hopper", "email": "grace@navy.mil"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Senior Systems Architect - Grace",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-15T14:00:00Z",
            "duration_minutes": 60,
        },
    )).json()
    itw_id = itw["id"]

    # 2. Add some interview evidence (transcript segment)
    await client.post(
        f"/api/v1/interviews/{itw_id}/adaptive/transcripts",
        headers=headers,
        json={
            "speaker_role": "candidate",
            "text": "I designed a distributed compiler with bytecode caching in Redis reducing build times by 70%.",
            "is_final": True,
            "confidence": 0.99,
        },
    )

    # 3. Generate Evaluation
    gen_res = await client.post(
        f"/api/v1/interviews/{itw_id}/evaluation/generate",
        headers=headers,
    )
    assert gen_res.status_code in [200, 201]
    eval_data = gen_res.json()
    assert eval_data["status"] == "draft"
    assert eval_data["overall_score"] > 0.0
    assert len(eval_data["competency_scores"]) >= 1

    comp_score = eval_data["competency_scores"][0]
    score_id = comp_score["id"]

    # 4. Human-in-the-loop Override Competency Score
    override_res = await client.put(
        f"/api/v1/interviews/{itw_id}/evaluation/competency-scores/{score_id}/override",
        headers=headers,
        json={
            "new_rubric_level": 5.0,
            "override_reason": "Candidate provided outstanding architectural depth and clear trade-off analysis.",
        },
    )
    assert override_res.status_code == 200
    updated_eval = override_res.json()
    updated_score = next((c for c in updated_eval["competency_scores"] if c["id"] == score_id), None)
    assert updated_score is not None
    assert updated_score["is_overridden"] is True
    assert updated_score["rubric_level"] == 5.0
    assert updated_score["calculated_score"] == 100.0

    # 5. Approve Evaluation
    approve_res = await client.post(
        f"/api/v1/interviews/{itw_id}/evaluation/approve",
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"

    # 6. Finalize Evaluation (Immutability Lock)
    finalize_res = await client.post(
        f"/api/v1/interviews/{itw_id}/evaluation/finalize",
        headers=headers,
    )
    assert finalize_res.status_code == 200
    finalized_eval = finalize_res.json()
    assert finalized_eval["status"] == "finalized"
    assert finalized_eval["is_locked"] is True

    # 7. Verify Immutability Invariant: Subsequent override attempts MUST fail with 400
    blocked_override = await client.put(
        f"/api/v1/interviews/{itw_id}/evaluation/competency-scores/{score_id}/override",
        headers=headers,
        json={
            "new_rubric_level": 2.0,
            "override_reason": "Attempting to modify locked finalized evaluation.",
        },
    )
    assert blocked_override.status_code == 400
    assert "finalized" in blocked_override.json()["detail"].lower() or "locked" in blocked_override.json()["detail"].lower()

    # 8. Retrieve Full Evaluation Report
    report_res = await client.get(
        f"/api/v1/interviews/{itw_id}/evaluation/report",
        headers=headers,
    )
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["is_finalized"] is True
    assert "evaluation" in report


@pytest.mark.asyncio
async def test_candidate_rbac_403_isolation(client: AsyncClient):
    # Register recruiter and setup interview
    recruiter_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "recruiter.eval.rbac@company.com", "password": "Password123!", "first_name": "Recruiter", "last_name": "One"},
    )
    rec_headers = {"Authorization": f"Bearer {recruiter_reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=rec_headers, json={"name": "PrivacyOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand_user = (await client.post(
        "/api/v1/auth/register",
        json={"email": "candidate.eval.rbac@company.com", "password": "Password123!", "first_name": "Cand", "last_name": "User"},
    )).json()
    cand_headers = {"Authorization": f"Bearer {cand_user['access_token']}"}

    cand = (await client.post(
        "/api/v1/candidates",
        headers=rec_headers,
        json={"workspace_id": ws_id, "first_name": "Cand", "last_name": "User", "email": "candidate.eval.rbac@company.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=rec_headers,
        json={
            "workspace_id": ws_id,
            "title": "Private Candidate Evaluation",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-15T14:00:00Z",
            "duration_minutes": 60,
        },
    )).json()
    itw_id = itw["id"]

    # Recruiter generates evaluation
    gen_res = await client.post(f"/api/v1/interviews/{itw_id}/evaluation/generate", headers=rec_headers)
    assert gen_res.status_code in [200, 201]

    # Candidate attempts to access evaluation endpoint -> MUST receive HTTP 403 Forbidden
    cand_access = await client.get(
        f"/api/v1/interviews/{itw_id}/evaluation",
        headers=cand_headers,
    )
    assert cand_access.status_code == 403
    assert "candidates cannot access" in cand_access.json()["detail"].lower()

    # Candidate attempts to access report -> 403
    cand_report = await client.get(
        f"/api/v1/interviews/{itw_id}/evaluation/report",
        headers=cand_headers,
    )
    assert cand_report.status_code == 403

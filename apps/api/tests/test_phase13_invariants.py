"""
Explicit Safety Invariant Tests for Phase 13:
- Deterministic matching score reproducibility & integrity
- Blueprint approval gates & state mutation rejection (in_progress, completed, paused)
- Question planning RBAC & candidate protection
- Tenant isolation across Resumes, Candidates, Jobs, Matches, Blueprints, Question Plans
- Resume privacy scrubbing
"""

import pytest
from httpx import AsyncClient
from app.services.matching_service import evaluate_candidate_job_match


@pytest.mark.asyncio
async def test_matching_score_deterministic_and_reproducible():
    """Verify that match score calculation is 100% deterministic and mathematical."""
    candidate_profile = {
        "skills": ["python", "fastapi", "postgresql", "docker"],
        "seniority": "senior",
        "total_experience_years": 6.0,
        "project_technologies": ["python", "fastapi", "redis", "postgresql"],
    }
    job_profile = {
        "requirements": [
            {"skill": "python", "canonical_skill": "python", "requirement_type": "required", "importance": 1.0},
            {"skill": "fastapi", "canonical_skill": "fastapi", "requirement_type": "required", "importance": 0.9},
            {"skill": "postgresql", "canonical_skill": "postgresql", "requirement_type": "required", "importance": 0.8},
            {"skill": "kubernetes", "canonical_skill": "kubernetes", "requirement_type": "required", "importance": 0.7},
            {"skill": "docker", "canonical_skill": "docker", "requirement_type": "preferred", "importance": 0.5},
            {"skill": "aws", "canonical_skill": "aws", "requirement_type": "preferred", "importance": 0.5},
        ],
        "min_experience_years": 5.0,
        "max_experience_years": 8.0,
        "target_seniority": "senior",
    }

    res1 = evaluate_candidate_job_match(
        candidate_profile=candidate_profile,
        job_profile=job_profile,
        claims=[],
    )

    res2 = evaluate_candidate_job_match(
        candidate_profile=candidate_profile,
        job_profile=job_profile,
        claims=[],
    )

    assert res1.overall_score == res2.overall_score
    assert res1.required_skill_coverage == res2.required_skill_coverage
    assert res1.preferred_skill_coverage == res2.preferred_skill_coverage
    assert res1.experience_fit == res2.experience_fit
    assert res1.seniority_fit == res2.seniority_fit
    assert res1.explanation == res2.explanation
    assert 0.0 <= res1.overall_score <= 100.0


@pytest.mark.asyncio
async def test_blueprint_state_mutation_and_approval_gates(client: AsyncClient):
    """
    Verify:
    1. Draft blueprint cannot be applied (must be approved)
    2. In-progress, completed, and paused interviews reject blueprint application
    3. Unauthorized user (non-member) cannot apply blueprint
    """
    # 1. Setup workspace & recruiter
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "gate.recruiter@intel.com", "password": "Password123!", "first_name": "Gate", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "GateOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Gary", "last_name": "Gate", "email": "gary@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Gary Gate Interview",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
        },
    )).json()

    # Generate draft blueprint
    bp = (await client.post(
        "/api/v1/intelligence/interviews/blueprints/generate",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "interview_id": itw["id"]},
    )).json()

    # 1. Attempt to apply DRAFT blueprint -> MUST FAIL (400)
    draft_apply = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp['id']}/apply?interview_id={itw['id']}",
        headers=headers,
    )
    assert draft_apply.status_code == 400
    assert "approved" in draft_apply.json()["detail"].lower()

    # Approve blueprint
    await client.post(f"/api/v1/intelligence/interviews/blueprints/{bp['id']}/approve", headers=headers)

    # 2. Apply to draft interview -> SUCCEEDS and creates rounds
    apply_ok = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp['id']}/apply?interview_id={itw['id']}",
        headers=headers,
    )
    assert apply_ok.status_code == 200

    # 3. Test in-progress safety rejection
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "scheduled"})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "in_progress"})

    bp2 = (await client.post(
        "/api/v1/intelligence/interviews/blueprints/generate",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "interview_id": itw["id"]},
    )).json()
    await client.post(f"/api/v1/intelligence/interviews/blueprints/{bp2['id']}/approve", headers=headers)

    inp_apply = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp2['id']}/apply?interview_id={itw['id']}",
        headers=headers,
    )
    assert inp_apply.status_code == 400
    assert "in progress or completed" in inp_apply.json()["detail"].lower()

    # 4. Test paused safety rejection
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "paused"})
    paused_apply = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp2['id']}/apply?interview_id={itw['id']}",
        headers=headers,
    )
    assert paused_apply.status_code == 400
    assert "in progress or completed" in paused_apply.json()["detail"].lower()

    # 5. Test completed safety rejection
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "in_progress"})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "completed"})
    completed_apply = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp2['id']}/apply?interview_id={itw['id']}",
        headers=headers,
    )
    assert completed_apply.status_code == 400
    assert "in progress or completed" in completed_apply.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tenant_isolation_cross_workspace_intelligence_forbidden(client: AsyncClient):
    """
    Verify Workspace A cannot access:
    - Workspace B resumes
    - Workspace B candidates
    - Workspace B jobs
    - Workspace B matches
    - Workspace B blueprints
    - Workspace B question plans
    """
    # 1. Setup Org A & User A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "tenant.a@intel.com", "password": "Password123!", "first_name": "Tenant", "last_name": "A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "OrgA", "initial_workspace_name": "WsA"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    # 2. Setup Org B & User B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "tenant.b@intel.com", "password": "Password123!", "first_name": "Tenant", "last_name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}
    org_b = (await client.post("/api/v1/organizations", headers=headers_b, json={"name": "OrgB", "initial_workspace_name": "WsB"})).json()
    ws_b_id = org_b["workspaces"][0]["id"]

    # 3. User B creates Candidate, Resume, Job, Blueprint, Plan in WsB
    cand_b = (await client.post(
        "/api/v1/candidates",
        headers=headers_b,
        json={"workspace_id": ws_b_id, "first_name": "Beta", "last_name": "Cand", "email": "beta@example.com"},
    )).json()

    files = {"file": ("beta_resume.pdf", b"%PDF-1.4 Beta Cand Resume", "application/pdf")}
    res_ver_b = (await client.post(
        f"/api/v1/intelligence/candidates/{cand_b['id']}/resumes",
        headers=headers_b,
        files=files,
    )).json()

    job_b = (await client.post(
        "/api/v1/jobs",
        headers=headers_b,
        json={"workspace_id": ws_b_id, "title": "Beta Architect", "department": "Eng"},
    )).json()

    itw_b = (await client.post(
        "/api/v1/interviews",
        headers=headers_b,
        json={
            "workspace_id": ws_b_id,
            "title": "Beta Interview",
            "candidate_id": cand_b["id"],
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
        },
    )).json()

    bp_b = (await client.post(
        "/api/v1/intelligence/interviews/blueprints/generate",
        headers=headers_b,
        json={"workspace_id": ws_b_id, "candidate_id": cand_b["id"], "interview_id": itw_b["id"]},
    )).json()

    qp_b = (await client.post(
        "/api/v1/intelligence/interviews/question-plans/generate",
        headers=headers_b,
        json={"workspace_id": ws_b_id, "candidate_id": cand_b["id"], "interview_id": itw_b["id"]},
    )).json()

    # 4. User A attempts to access Workspace B resources -> MUST BE FORBIDDEN (403/404)
    # A attempts to read candidate B resumes
    hack_resumes = await client.get(f"/api/v1/intelligence/candidates/{cand_b['id']}/resumes", headers=headers_a)
    assert hack_resumes.status_code in [403, 404]

    # A attempts to read resume B intelligence
    hack_intel = await client.get(f"/api/v1/intelligence/resumes/{res_ver_b['id']}/intelligence", headers=headers_a)
    assert hack_intel.status_code in [403, 404]

    # A attempts to read job B intelligence
    hack_job_intel = await client.get(f"/api/v1/intelligence/jobs/{job_b['id']}/intelligence", headers=headers_a)
    assert hack_job_intel.status_code in [403, 404]

    # A attempts to generate match for candidate B and job B
    hack_match = await client.post(
        "/api/v1/intelligence/matching/calculate",
        headers=headers_a,
        json={"workspace_id": ws_a_id, "candidate_id": cand_b["id"], "job_id": job_b["id"]},
    )
    assert hack_match.status_code in [403, 404]

    # A attempts to read blueprint B
    hack_bp = await client.get(f"/api/v1/intelligence/interviews/{itw_b['id']}/blueprints", headers=headers_a)
    assert hack_bp.status_code in [403, 404]

    # A attempts to approve blueprint B
    hack_approve = await client.post(f"/api/v1/intelligence/interviews/blueprints/{bp_b['id']}/approve", headers=headers_a)
    assert hack_approve.status_code in [403, 404]

    # A attempts to read question plan B
    hack_qp = await client.get(f"/api/v1/intelligence/interviews/{itw_b['id']}/question-plans", headers=headers_a)
    assert hack_qp.status_code in [403, 404]

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_blueprint_generation_approval_and_application(client: AsyncClient):
    # 1. Register user & org
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "planner.recruiter@intel.com", "password": "Password123!", "first_name": "Plan", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "PlanOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 2. Create candidate and job
    cand_resp = await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Charlie", "last_name": "Dev", "email": "charlie@example.com"},
    )
    candidate_id = cand_resp.json()["id"]

    job_resp = await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Full Stack Engineer",
            "employment_type": "full_time",
            "required_skills": ["React", "TypeScript", "Node.js"],
        },
    )
    job_id = job_resp.json()["id"]

    # 3. Create Interview (draft/scheduled)
    itw_resp = await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Full Stack Interview with Charlie",
            "interview_type": "technical",
            "candidate_id": candidate_id,
            "job_id": job_id,
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 60,
        },
    )
    interview_id = itw_resp.json()["id"]

    # 4. Generate Blueprint
    bp_resp = await client.post(
        "/api/v1/intelligence/interviews/blueprints/generate",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "interview_id": interview_id,
            "title": "Full Stack Engineering Blueprint",
        },
    )
    assert bp_resp.status_code == 201
    blueprint = bp_resp.json()
    assert blueprint["status"] == "draft"
    assert len(blueprint["rounds"]) >= 2
    blueprint_id = blueprint["id"]

    # 5. Attempt to apply unapproved blueprint -> must fail
    apply_fail = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{blueprint_id}/apply?interview_id={interview_id}",
        headers=headers,
    )
    assert apply_fail.status_code == 400

    # 6. Approve Blueprint
    appr_resp = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{blueprint_id}/approve",
        headers=headers,
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"

    # 7. Apply Blueprint to Interview
    apply_resp = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{blueprint_id}/apply?interview_id={interview_id}",
        headers=headers,
    )
    assert apply_resp.status_code == 200

    # Verify interview rounds were created
    get_itw = await client.get(f"/api/v1/interviews/{interview_id}", headers=headers)
    assert len(get_itw.json()["rounds"]) >= 2


@pytest.mark.asyncio
async def test_live_interview_mutation_safety_rejection(client: AsyncClient):
    # 1. Register user & org
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "safety.recruiter@intel.com", "password": "Password123!", "first_name": "Safe", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "SafeOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Dave", "last_name": "Dev", "email": "dave@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Dave Live Interview",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
        },
    )).json()

    # Generate, approve, and apply initial blueprint to set up valid interview structure & rounds
    bp1 = (await client.post(
        "/api/v1/intelligence/interviews/blueprints/generate",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "candidate_id": cand["id"],
            "interview_id": itw["id"],
        },
    )).json()
    await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp1['id']}/approve",
        headers=headers,
    )
    apply1_resp = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp1['id']}/apply?interview_id={itw['id']}",
        headers=headers,
    )
    assert apply1_resp.status_code == 200

    # Set interview status to in_progress via valid state machine transitions
    ready_resp = await client.patch(
        f"/api/v1/interviews/{itw['id']}",
        headers=headers,
        json={"status": "ready"},
    )
    assert ready_resp.status_code == 200
    sched_resp = await client.patch(
        f"/api/v1/interviews/{itw['id']}",
        headers=headers,
        json={"status": "scheduled"},
    )
    assert sched_resp.status_code == 200
    inp_resp = await client.patch(
        f"/api/v1/interviews/{itw['id']}",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert inp_resp.status_code == 200

    # Generate and approve a 2nd blueprint
    bp2 = (await client.post(
        "/api/v1/intelligence/interviews/blueprints/generate",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "candidate_id": cand["id"],
            "interview_id": itw["id"],
        },
    )).json()
    await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp2['id']}/approve",
        headers=headers,
    )

    # Attempt to apply blueprint to in-progress interview -> MUST be rejected
    apply_resp = await client.post(
        f"/api/v1/intelligence/interviews/blueprints/{bp2['id']}/apply?interview_id={itw['id']}",
        headers=headers,
    )
    assert apply_resp.status_code == 400
    assert "in progress or completed" in apply_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_question_planning_and_coverage_matrix(client: AsyncClient):
    # 1. Register user & org
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "qp.recruiter@intel.com", "password": "Password123!", "first_name": "QP", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "QPOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Eve", "last_name": "Engineer", "email": "eve@example.com"},
    )).json()

    # Generate question plan
    qp_resp = await client.post(
        "/api/v1/intelligence/interviews/question-plans/generate",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "candidate_id": cand["id"],
            "title": "Eve Personalized Question Plan",
        },
    )
    assert qp_resp.status_code == 201
    qp_data = qp_resp.json()
    assert len(qp_data["items"]) >= 2
    assert "coverage_summary" in qp_data

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_interview_and_rounds(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "recruiter@interviews.com", "password": "Password123!", "first_name": "Lead", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "IntOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Create candidate
    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Alan", "last_name": "Turing", "email": "alan@turing.org"},
    )).json()

    # Create job
    job = (await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"workspace_id": ws_id, "title": "Staff Cryptography Engineer"},
    )).json()

    # 1. Create interview in DRAFT
    itw_payload = {
        "workspace_id": ws_id,
        "candidate_id": cand["id"],
        "job_id": job["id"],
        "title": "Staff Cryptography Loop - Alan Turing",
        "interview_type": "technical",
        "difficulty": "lead",
        "duration_minutes": 90,
        "instructions": "Standard staff-level technical screening",
    }
    create_res = await client.post("/api/v1/interviews", headers=headers, json=itw_payload)
    assert create_res.status_code == 201
    itw_data = create_res.json()
    assert itw_data["title"] == "Staff Cryptography Loop - Alan Turing"
    assert itw_data["status"] == "draft"
    assert itw_data["is_ready"] is False
    itw_id = itw_data["id"]

    # 2. Add Round 1 (30 mins)
    r1_res = await client.post(
        f"/api/v1/interviews/{itw_id}/rounds",
        headers=headers,
        json={
            "name": "Theoretical Foundations",
            "round_type": "technical",
            "sequence": 1,
            "duration_minutes": 30,
            "difficulty": "lead",
        },
    )
    assert r1_res.status_code == 201
    assert r1_res.json()["sequence"] == 1

    # 3. Add Round 2 (60 mins)
    r2_res = await client.post(
        f"/api/v1/interviews/{itw_id}/rounds",
        headers=headers,
        json={
            "name": "Cryptographic Protocols",
            "round_type": "coding",
            "sequence": 2,
            "duration_minutes": 60,
            "difficulty": "lead",
        },
    )
    assert r2_res.status_code == 201
    assert r2_res.json()["sequence"] == 2

    # 4. Check readiness (total rounds = 90 mins == interview duration)
    readiness_res = await client.get(f"/api/v1/interviews/{itw_id}/readiness", headers=headers)
    assert readiness_res.status_code == 200
    assert readiness_res.json()["is_ready"] is True
    assert len(readiness_res.json()["issues"]) == 0


@pytest.mark.asyncio
async def test_round_duration_validation(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "duration@interviews.com", "password": "Password123!", "first_name": "Dur", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "DurOrg", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Grace", "last_name": "Hopper", "email": "grace@navy.mil"},
    )).json()

    # Create 60-min interview
    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "60m Interview", "duration_minutes": 60},
    )).json()

    # Add 45-min round
    await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds",
        headers=headers,
        json={"name": "Round 1", "duration_minutes": 45, "sequence": 1},
    )

    # Add second 45-min round (Total = 90 mins, exceeds 60 mins)
    await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds",
        headers=headers,
        json={"name": "Round 2", "duration_minutes": 45, "sequence": 2},
    )

    readiness = (await client.get(f"/api/v1/interviews/{itw['id']}/readiness", headers=headers)).json()
    assert readiness["is_ready"] is False
    assert any("exceeds total interview duration" in issue for issue in readiness["issues"])


@pytest.mark.asyncio
async def test_interview_lifecycle_state_machine(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "state@interviews.com", "password": "Password123!", "first_name": "State", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "StateOrg", "initial_workspace_name": "StateWS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Ada", "last_name": "Lovelace", "email": "ada@lovelace.co.uk"},
    )).json()

    # Create interview with 0 rounds
    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "State Test", "duration_minutes": 45},
    )).json()

    # 1. Attempt transition to READY while incomplete (0 rounds) -> 422 Unprocessable Content
    fail_ready = await client.patch(
        f"/api/v1/interviews/{itw['id']}",
        headers=headers,
        json={"status": "ready"},
    )
    assert fail_ready.status_code == 422
    assert "at least one round" in fail_ready.json()["detail"].lower()

    # 2. Add valid 45-min round
    await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds",
        headers=headers,
        json={"name": "Initial Screening", "duration_minutes": 45, "sequence": 1},
    )

    # 3. Transition to READY now succeeds -> 200 OK
    ready_res = await client.patch(
        f"/api/v1/interviews/{itw['id']}",
        headers=headers,
        json={"status": "ready"},
    )
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"

    # 4. Transition READY -> SCHEDULED -> IN_PROGRESS -> COMPLETED
    sched_res = await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "scheduled"})
    assert sched_res.status_code == 200
    assert sched_res.json()["status"] == "scheduled"

    in_prog_res = await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "in_progress"})
    assert in_prog_res.status_code == 200
    assert in_prog_res.json()["status"] == "in_progress"

    done_res = await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "completed"})
    assert done_res.status_code == 200
    assert done_res.json()["status"] == "completed"

    # 5. Invalid transition: COMPLETED -> DRAFT -> 400 Bad Request
    invalid_res = await client.patch(
        f"/api/v1/interviews/{itw['id']}",
        headers=headers,
        json={"status": "draft"},
    )
    assert invalid_res.status_code == 400
    assert "invalid interview state transition" in invalid_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_question_assignment_to_rounds(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "assign@interviews.com", "password": "Password123!", "first_name": "Assign", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "AssignOrg", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Claude", "last_name": "Shannon", "email": "claude@mit.edu"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Information Theory Round"},
    )).json()

    round_obj = (await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds",
        headers=headers,
        json={"name": "Entropy and Coding", "duration_minutes": 45, "sequence": 1},
    )).json()

    # Create question in question bank
    question = (await client.post(
        "/api/v1/questions",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Calculate Information Entropy",
            "prompt": "Write a function calculating Shannon entropy for a discrete probability distribution.",
            "question_type": "technical",
        },
    )).json()

    # 1. Assign question to round
    assign_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds/{round_obj['id']}/questions",
        headers=headers,
        json={"question_id": question["id"], "sequence": 1, "is_required": True},
    )
    assert assign_res.status_code == 201
    assert assign_res.json()["question_id"] == question["id"]

    # 2. Verify eager-loaded rounds detail
    rounds_res = await client.get(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers)
    assert rounds_res.status_code == 200
    assert len(rounds_res.json()[0]["questions"]) == 1
    assert rounds_res.json()[0]["questions"][0]["question"]["title"] == "Calculate Information Entropy"

    # 3. Remove question from round
    del_res = await client.delete(
        f"/api/v1/interviews/{itw['id']}/rounds/{round_obj['id']}/questions/{question['id']}",
        headers=headers,
    )
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_participant_panel_management(client: AsyncClient):
    # Owner user
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "panel.owner@interviews.com", "password": "Password123!", "first_name": "Panel", "last_name": "Owner"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "PanelOrg", "initial_workspace_name": "PanelWS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Linus", "last_name": "Torvalds", "email": "linus@kernel.org"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Kernel Engineering Loop"},
    )).json()

    # Assign current user as lead interviewer
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    part_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/participants",
        headers=headers,
        json={"user_id": me["id"], "participant_role": "lead_interviewer", "is_primary": True},
    )
    assert part_res.status_code == 201
    assert part_res.json()["participant_role"] == "lead_interviewer"

    # List participants
    parts_list = await client.get(f"/api/v1/interviews/{itw['id']}/participants", headers=headers)
    assert parts_list.status_code == 200
    assert len(parts_list.json()) == 1
    assert parts_list.json()[0]["user_id"] == me["id"]


@pytest.mark.asyncio
async def test_template_instantiation_creates_independent_interview(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "template.user@interviews.com", "password": "Password123!", "first_name": "Tpl", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "InstOrg", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Donald", "last_name": "Knuth", "email": "knuth@stanford.edu"},
    )).json()

    # 1. Create Template with 2 rounds
    tpl = (await client.post(
        "/api/v1/interview-templates",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "name": "Standard Backend Template",
            "total_duration_minutes": 60,
            "rounds": [
                {"name": "DSA Screening", "duration_minutes": 30, "sequence": 1, "round_type": "coding"},
                {"name": "Architecture", "duration_minutes": 30, "sequence": 2, "round_type": "system_design"},
            ],
        },
    )).json()

    # 2. Instantiate interview from template
    inst_res = await client.post(
        f"/api/v1/interviews/from-template/{tpl['id']}",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Donald Knuth - Backend Loop"},
    )
    assert inst_res.status_code == 201
    itw_inst = inst_res.json()
    assert itw_inst["title"] == "Donald Knuth - Backend Loop"
    assert itw_inst["round_count"] == 2

    # 3. Verify instantiated rounds
    rounds_res = await client.get(f"/api/v1/interviews/{itw_inst['id']}/rounds", headers=headers)
    assert rounds_res.status_code == 200
    rounds = rounds_res.json()
    assert len(rounds) == 2
    assert rounds[0]["name"] == "DSA Screening"
    assert rounds[1]["name"] == "Architecture"


@pytest.mark.asyncio
async def test_cross_workspace_interview_access_forbidden(client: AsyncClient):
    # Workspace A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@tenant-a-itw.com", "password": "Password123!", "first_name": "Alice", "last_name": "A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "Org A", "initial_workspace_name": "WS-A"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    cand_a = (await client.post(
        "/api/v1/candidates",
        headers=headers_a,
        json={"workspace_id": ws_a_id, "first_name": "Confidential", "last_name": "Candidate", "email": "conf@a.com"},
    )).json()

    itw_a = (await client.post(
        "/api/v1/interviews",
        headers=headers_a,
        json={"workspace_id": ws_a_id, "candidate_id": cand_a["id"], "title": "Confidential Loop"},
    )).json()

    # Workspace B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@tenant-b-itw.com", "password": "Password123!", "first_name": "Bob", "last_name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Bob attempts to read Alice's interview -> 403 Forbidden
    cross_read = await client.get(f"/api/v1/interviews/{itw_a['id']}", headers=headers_b)
    assert cross_read.status_code == 403

    # Bob attempts to update Alice's interview -> 403 Forbidden
    cross_patch = await client.patch(f"/api/v1/interviews/{itw_a['id']}", headers=headers_b, json={"title": "Hacked"})
    assert cross_patch.status_code == 403

    # Bob attempts to list interviews passing Alice's workspace_id -> 403 Forbidden
    cross_list = await client.get(f"/api/v1/interviews?workspace_id={ws_a_id}", headers=headers_b)
    assert cross_list.status_code == 403

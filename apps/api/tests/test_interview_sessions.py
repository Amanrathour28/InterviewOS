from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_session_creation_and_idempotency(client: AsyncClient):
    # 1. Setup user, org, candidate, interview
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "session.lead@interviewos.com", "password": "Password123!", "first_name": "Session", "last_name": "Lead"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "LiveSessionCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Alan", "last_name": "Turing", "email": "alan@turing.ac.uk"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Morphogenesis & Computing", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "Theory", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # 2. Create session
    sess_res1 = await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)
    assert sess_res1.status_code == 201
    sess1 = sess_res1.json()
    assert sess1["status"] == "waiting"
    assert sess1["current_stage"] == "introduction"
    assert sess1["interview_id"] == itw["id"]

    # 3. Idempotent check: Calling again returns the EXACT same session
    sess_res2 = await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)
    assert sess_res2.status_code == 201
    sess2 = sess_res2.json()
    assert sess2["id"] == sess1["id"]


@pytest.mark.asyncio
async def test_session_lifecycle_state_machine(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "lifecycle.lead@interviewos.com", "password": "Password123!", "first_name": "Lifecycle", "last_name": "Lead"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "LifecycleCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Claude", "last_name": "Shannon", "email": "claude@mit.edu"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Information Theory", "duration_minutes": 60},
    )).json()
    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "R1", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # Create session -> status = waiting
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)).json()
    sess_id = session["id"]

    # 1. Start session -> status = active
    start_res = await client.post(f"/api/v1/sessions/{sess_id}/start", headers=headers)
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "active"
    assert start_res.json()["started_at"] is not None

    # Parent interview is now IN_PROGRESS
    itw_res = (await client.get(f"/api/v1/interviews/{itw['id']}", headers=headers)).json()
    assert itw_res["status"] == "in_progress"

    # 2. Change stage to technical
    stage_res = await client.post(
        f"/api/v1/sessions/{sess_id}/stage",
        headers=headers,
        json={"stage": "technical", "reason": "Moving past introduction"},
    )
    assert stage_res.status_code == 200
    assert stage_res.json()["current_stage"] == "technical"

    # 3. Pause session -> status = paused
    pause_res = await client.post(
        f"/api/v1/sessions/{sess_id}/pause",
        headers=headers,
        json={"reason": "Technical audio glitch check"},
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "paused"
    assert pause_res.json()["paused_at"] is not None

    # Cannot pause already paused session
    re_pause = await client.post(f"/api/v1/sessions/{sess_id}/pause", headers=headers)
    assert re_pause.status_code == 200  # Idempotent

    # 4. Resume session -> status = active
    resume_res = await client.post(f"/api/v1/sessions/{sess_id}/resume", headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "active"
    assert resume_res.json()["paused_at"] is None

    # 5. End session -> status = completed
    end_res = await client.post(
        f"/api/v1/sessions/{sess_id}/end",
        headers=headers,
        json={"reason": "All rounds finished successfully"},
    )
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "completed"
    assert end_res.json()["ended_at"] is not None

    # Parent interview is now COMPLETED
    itw_completed = (await client.get(f"/api/v1/interviews/{itw['id']}", headers=headers)).json()
    assert itw_completed["status"] == "completed"

    # 6. Invalid transition: Cannot start completed session (400)
    invalid_start = await client.post(f"/api/v1/sessions/{sess_id}/start", headers=headers)
    assert invalid_start.status_code == 400
    assert "cannot start session" in invalid_start.json()["detail"].lower()

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_session_state_machine_and_timer_accuracy(client: AsyncClient):
    """Test session lifecycle transitions: WAITING -> ACTIVE -> PAUSED -> ACTIVE -> COMPLETED and timer math."""
    # 1. Register Interviewer & Setup Interview
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"timer.lead.{uuid.uuid4().hex[:6]}@interviewos.com", "password": "Password123!", "first_name": "Timer", "last_name": "Lead"},
    )
    headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "TimerOrg", "initial_workspace_name": "Engineering"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Alice", "last_name": "Applicant", "email": f"alice.{uuid.uuid4().hex[:6]}@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Full Stack Architecture", "duration_minutes": 45},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "Intro", "duration_minutes": 10, "sequence": 1})
    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "Coding", "duration_minutes": 35, "sequence": 2})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # 2. Initialize Session
    sess = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)).json()
    sess_id = sess["id"]
    assert sess["status"] == "waiting"

    # Detail view in waiting state
    detail_waiting = (await client.get(f"/api/v1/sessions/{sess_id}", headers=headers)).json()
    assert detail_waiting["status"] == "waiting"
    assert detail_waiting["current_elapsed_seconds"] == 0
    assert detail_waiting["remaining_seconds"] == 45 * 60
    assert detail_waiting["is_paused"] is False

    # 3. Start Session
    start_res = await client.post(f"/api/v1/sessions/{sess_id}/start", headers=headers)
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "active"

    # 4. Pause Session
    pause_res = await client.post(f"/api/v1/sessions/{sess_id}/pause", json={"reason": "Bio break"}, headers=headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "paused"

    detail_paused = (await client.get(f"/api/v1/sessions/{sess_id}", headers=headers)).json()
    assert detail_paused["status"] == "paused"
    assert detail_paused["is_paused"] is True

    # 5. Resume Session
    resume_res = await client.post(f"/api/v1/sessions/{sess_id}/resume", headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "active"

    # 6. End Session
    end_res = await client.post(f"/api/v1/sessions/{sess_id}/end", json={"reason": "Interview completed successfully"}, headers=headers)
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "completed"

    # Cannot restart completed session
    restart_res = await client.post(f"/api/v1/sessions/{sess_id}/start", headers=headers)
    assert restart_res.status_code == 400


@pytest.mark.asyncio
async def test_stage_transitions_and_durable_event_logging(client: AsyncClient):
    """Test changing interview stages and verifying durable event logging."""
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"stage.lead.{uuid.uuid4().hex[:6]}@interviewos.com", "password": "Password123!", "first_name": "Stage", "last_name": "Lead"},
    )
    headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "StageOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Bob", "last_name": "Builder", "email": f"bob.{uuid.uuid4().hex[:6]}@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "System Design Round", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "System Design", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    sess = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)).json()
    sess_id = sess["id"]

    await client.post(f"/api/v1/sessions/{sess_id}/start", headers=headers)

    # 1. Transition to Technical Stage
    stage1 = await client.post(f"/api/v1/sessions/{sess_id}/stage", json={"stage": "technical"}, headers=headers)
    assert stage1.status_code == 200
    assert stage1.json()["current_stage"] == "technical"

    # 2. Transition to Coding Stage
    stage2 = await client.post(f"/api/v1/sessions/{sess_id}/stage", json={"stage": "coding"}, headers=headers)
    assert stage2.status_code == 200
    assert stage2.json()["current_stage"] == "coding"

    # 3. Transition to System Design Stage
    stage3 = await client.post(f"/api/v1/sessions/{sess_id}/stage", json={"stage": "system_design"}, headers=headers)
    assert stage3.status_code == 200
    assert stage3.json()["current_stage"] == "system_design"

    # 4. Verify durable event stream
    events_res = await client.get(f"/api/v1/sessions/{sess_id}/events", headers=headers)
    assert events_res.status_code == 200
    event_types = [e["event_type"] for e in events_res.json()]
    assert "SESSION_CREATED" in event_types
    assert "SESSION_STARTED" in event_types
    assert "STAGE_CHANGED" in event_types


@pytest.mark.asyncio
async def test_interviewer_structured_notes_isolation(client: AsyncClient):
    """Test interviewer structured note creation and strict candidate isolation."""
    # 1. Setup Session
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"notes.lead.{uuid.uuid4().hex[:6]}@interviewos.com", "password": "Password123!", "first_name": "Notes", "last_name": "Lead"},
    )
    interviewer_headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    candidate_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"cand.notes.{uuid.uuid4().hex[:6]}@example.com", "password": "Password123!", "first_name": "Charlie", "last_name": "Candidate"},
    )
    candidate_headers = {"Authorization": f"Bearer {candidate_res.json()['access_token']}"}

    org = (await client.post("/api/v1/organizations", headers=interviewer_headers, json={"name": "NotesOrg", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "first_name": "Charlie", "last_name": "Candidate", "email": f"cand.notes.{uuid.uuid4().hex[:6]}@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Senior Engineer Round", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=interviewer_headers, json={"name": "Tech", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=interviewer_headers, json={"status": "ready"})

    sess = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=interviewer_headers)).json()
    sess_id = sess["id"]

    # 2. Interviewer creates notes
    note1 = await client.post(
        f"/api/v1/sessions/{sess_id}/notes",
        json={
            "category": "coding",
            "content": "Excellent grasp of two-pointer optimization and edge cases.",
            "rating": 5,
            "tags": ["algorithms", "optimal-time-complexity"],
        },
        headers=interviewer_headers,
    )
    assert note1.status_code == 201
    note1_id = note1.json()["id"]

    note2 = await client.post(
        f"/api/v1/sessions/{sess_id}/notes",
        json={
            "category": "behavioral",
            "content": "Articulated past conflict resolution clearly.",
            "rating": 4,
            "tags": ["leadership", "communication"],
        },
        headers=interviewer_headers,
    )
    assert note2.status_code == 201

    # 3. Interviewer lists notes with filter
    notes_list = await client.get(f"/api/v1/sessions/{sess_id}/notes?category=coding", headers=interviewer_headers)
    assert notes_list.status_code == 200
    assert len(notes_list.json()) == 1
    assert notes_list.json()[0]["category"] == "coding"

    # 4. Candidate attempts to access notes -> 403 Forbidden
    cand_get = await client.get(f"/api/v1/sessions/{sess_id}/notes", headers=candidate_headers)
    assert cand_get.status_code == 403

    cand_post = await client.post(
        f"/api/v1/sessions/{sess_id}/notes",
        json={"category": "general", "content": "Hacking notes"},
        headers=candidate_headers,
    )
    assert cand_post.status_code == 403


@pytest.mark.asyncio
async def test_activity_timeline_filtering(client: AsyncClient):
    """Test retrieving structured session activity timeline and filtering by category."""
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"timeline.lead.{uuid.uuid4().hex[:6]}@interviewos.com", "password": "Password123!", "first_name": "Timeline", "last_name": "Lead"},
    )
    headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "TimelineOrg", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Dan", "last_name": "Developer", "email": f"dan.{uuid.uuid4().hex[:6]}@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Timeline Test Round", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "Round 1", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    sess = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)).json()
    sess_id = sess["id"]

    await client.post(f"/api/v1/sessions/{sess_id}/start", headers=headers)
    await client.post(f"/api/v1/sessions/{sess_id}/stage", json={"stage": "coding"}, headers=headers)
    await client.post(f"/api/v1/sessions/{sess_id}/pause", json={"reason": "Short break"}, headers=headers)
    await client.post(f"/api/v1/sessions/{sess_id}/resume", headers=headers)

    # 1. Timeline All
    all_timeline = await client.get(f"/api/v1/sessions/{sess_id}/timeline", headers=headers)
    assert all_timeline.status_code == 200
    assert len(all_timeline.json()) >= 4

    # 2. Timeline filtered by stages
    stage_timeline = await client.get(f"/api/v1/sessions/{sess_id}/timeline?category=stages", headers=headers)
    assert stage_timeline.status_code == 200
    assert len(stage_timeline.json()) >= 1
    assert all(item["category"] == "stages" for item in stage_timeline.json())


@pytest.mark.asyncio
async def test_candidate_waiting_room_and_health(client: AsyncClient):
    """Test candidate waiting room endpoint and session health diagnostic."""
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"health.lead.{uuid.uuid4().hex[:6]}@interviewos.com", "password": "Password123!", "first_name": "Health", "last_name": "Lead"},
    )
    headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "HealthOrg", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Eve", "last_name": "Engineer", "email": f"eve.{uuid.uuid4().hex[:6]}@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Candidate Experience Test", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "Intro", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    sess = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)).json()
    sess_id = sess["id"]

    # 1. Candidate Waiting Room view
    wr_res = await client.get(f"/api/v1/sessions/{sess_id}/waiting-room", headers=headers)
    assert wr_res.status_code == 200
    wr_data = wr_res.json()
    assert wr_data["interview_title"] == "Candidate Experience Test"
    assert wr_data["status"] == "waiting"
    assert "ice_servers" in wr_data

    # 2. Session Health
    health_res = await client.get(f"/api/v1/sessions/{sess_id}/health", headers=headers)
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["is_operational"] is True
    assert health_data["websocket_healthy"] is True

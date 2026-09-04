from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_interval_conflict_detection(client: AsyncClient):
    # 1. Register & setup org + workspace
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "conflict.lead@interviewos.com", "password": "Password123!", "first_name": "Conflict", "last_name": "Detector"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "ConflictCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "John", "last_name": "von Neumann", "email": "john@ias.edu"},
    )).json()

    # Interview A: 60 minutes
    itw_a = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Game Theory & Automata", "duration_minutes": 60},
    )).json()
    await client.post(f"/api/v1/interviews/{itw_a['id']}/rounds", headers=headers, json={"name": "Round 1", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw_a['id']}", headers=headers, json={"status": "ready"})

    # Schedule Interview A: Day 10 at 10:00 UTC (10:00 -> 11:00)
    base_time = (datetime.now(timezone.utc) + timedelta(days=10)).replace(hour=10, minute=0, second=0, microsecond=0)
    sched_a = await client.post(
        f"/api/v1/interviews/{itw_a['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": base_time.isoformat(), "timezone": "UTC"},
    )
    assert sched_a.status_code == 201

    # Interview B: 60 minutes with SAME candidate
    itw_b = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Quantum Foundations", "duration_minutes": 60},
    )).json()
    await client.post(f"/api/v1/interviews/{itw_b['id']}/rounds", headers=headers, json={"name": "Round 1", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw_b['id']}", headers=headers, json={"status": "ready"})

    # 1. Exact overlap: 10:00 -> 11:00 (Conflict 409)
    exact_res = await client.post(
        f"/api/v1/interviews/{itw_b['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": base_time.isoformat(), "timezone": "UTC"},
    )
    assert exact_res.status_code == 409
    assert "conflict" in exact_res.json()["detail"].lower()

    # 2. Partial start overlap: 10:30 -> 11:30 (Conflict 409)
    partial_start = base_time + timedelta(minutes=30)
    part_start_res = await client.post(
        f"/api/v1/interviews/{itw_b['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": partial_start.isoformat(), "timezone": "UTC"},
    )
    assert part_start_res.status_code == 409

    # 3. Partial end overlap: 09:30 -> 10:30 (Conflict 409)
    partial_end = base_time - timedelta(minutes=30)
    part_end_res = await client.post(
        f"/api/v1/interviews/{itw_b['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": partial_end.isoformat(), "timezone": "UTC"},
    )
    assert part_end_res.status_code == 409

    # 4. Adjacent slot: 11:00 -> 12:00 (Allowed 201!)
    adjacent_time = base_time + timedelta(minutes=60)
    adjacent_res = await client.post(
        f"/api/v1/interviews/{itw_b['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": adjacent_time.isoformat(), "timezone": "UTC"},
    )
    assert adjacent_res.status_code == 201
    assert adjacent_res.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_interviewer_conflict_detection(client: AsyncClient):
    # 1. Register interviewer
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "panelist@interviewos.com", "password": "Password123!", "first_name": "Panelist", "last_name": "Expert"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "PanelCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Two different candidates
    cand1 = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "CandOne", "last_name": "Alpha", "email": "one@alpha.com"},
    )).json()

    cand2 = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "CandTwo", "last_name": "Beta", "email": "two@beta.com"},
    )).json()

    # Interview 1 (Assigned to Panelist)
    itw1 = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand1["id"], "title": "Loop 1", "duration_minutes": 60},
    )).json()
    await client.post(f"/api/v1/interviews/{itw1['id']}/rounds", headers=headers, json={"name": "R1", "duration_minutes": 60, "sequence": 1})
    await client.post(
        f"/api/v1/interviews/{itw1['id']}/participants",
        headers=headers,
        json={"user_id": me["id"], "participant_role": "lead_interviewer", "is_primary": True},
    )
    await client.patch(f"/api/v1/interviews/{itw1['id']}", headers=headers, json={"status": "ready"})

    # Schedule Interview 1 at 14:00 UTC
    sched_time = (datetime.now(timezone.utc) + timedelta(days=12)).replace(hour=14, minute=0, second=0, microsecond=0)
    await client.post(
        f"/api/v1/interviews/{itw1['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": sched_time.isoformat(), "timezone": "UTC"},
    )

    # Interview 2 (Also assigns SAME Panelist)
    itw2 = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand2["id"], "title": "Loop 2", "duration_minutes": 60},
    )).json()
    await client.post(f"/api/v1/interviews/{itw2['id']}/rounds", headers=headers, json={"name": "R1", "duration_minutes": 60, "sequence": 1})
    await client.post(
        f"/api/v1/interviews/{itw2['id']}/participants",
        headers=headers,
        json={"user_id": me["id"], "participant_role": "interviewer", "is_primary": False},
    )
    await client.patch(f"/api/v1/interviews/{itw2['id']}", headers=headers, json={"status": "ready"})

    # Attempt to schedule Interview 2 at 14:30 UTC -> Interviewer Conflict 409
    overlap_time = sched_time + timedelta(minutes=30)
    interviewer_conflict = await client.post(
        f"/api/v1/interviews/{itw2['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": overlap_time.isoformat(), "timezone": "UTC"},
    )
    assert interviewer_conflict.status_code == 409
    assert "interviewer" in interviewer_conflict.json()["detail"].lower()

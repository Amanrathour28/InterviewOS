import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_session_event_sequencing_and_retrieval(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "events.lead@interviewos.com", "password": "Password123!", "first_name": "Events", "last_name": "Auditor"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "EventCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Ada", "last_name": "Lovelace", "email": "ada@lovelace.org"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Analytical Engine Code", "duration_minutes": 60},
    )).json()
    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "R1", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # 1. Create session (Event 1: SESSION_CREATED)
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)).json()
    sess_id = session["id"]

    # 2. Start session (Event 2: SESSION_STARTED)
    await client.post(f"/api/v1/sessions/{sess_id}/start", headers=headers)

    # 3. Change stage (Event 3: STAGE_CHANGED)
    await client.post(
        f"/api/v1/sessions/{sess_id}/stage",
        headers=headers,
        json={"stage": "coding", "reason": "Begin live algorithm challenge"},
    )

    # 4. Pause session (Event 4: SESSION_PAUSED)
    await client.post(f"/api/v1/sessions/{sess_id}/pause", headers=headers, json={"reason": "Short break"})

    # 5. Resume session (Event 5: SESSION_RESUMED)
    await client.post(f"/api/v1/sessions/{sess_id}/resume", headers=headers)

    # 6. End session (Event 6: SESSION_ENDED)
    await client.post(f"/api/v1/sessions/{sess_id}/end", headers=headers, json={"reason": "Completed evaluation"})

    # 7. Fetch all events
    events_res = await client.get(f"/api/v1/sessions/{sess_id}/events", headers=headers)
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) == 6

    # Verify monotonic sequencing: 1, 2, 3, 4, 5, 6
    sequences = [e["sequence"] for e in events]
    assert sequences == [1, 2, 3, 4, 5, 6]

    # Verify event types
    event_types = [e["event_type"] for e in events]
    assert event_types == [
        "SESSION_CREATED",
        "SESSION_STARTED",
        "STAGE_CHANGED",
        "SESSION_PAUSED",
        "SESSION_RESUMED",
        "SESSION_ENDED",
    ]

    # 8. Filter with after_sequence=3 (should return events 4, 5, 6)
    filtered_res = await client.get(f"/api/v1/sessions/{sess_id}/events?after_sequence=3", headers=headers)
    assert filtered_res.status_code == 200
    filtered = filtered_res.json()
    assert len(filtered) == 3
    assert [e["sequence"] for e in filtered] == [4, 5, 6]

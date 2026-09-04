from datetime import datetime, time, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_recurring_availability_and_slots(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "avail@interviewos.com", "password": "Password123!", "first_name": "Avail", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "AvailCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 1. Create recurring Monday availability: 09:00 - 17:00
    avail_res = await client.post(
        "/api/v1/availability",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "day_of_week": 0,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "timezone": "UTC",
        },
    )
    assert avail_res.status_code == 201
    avail_data = avail_res.json()
    assert avail_data["day_of_week"] == 0
    assert avail_data["start_time"] == "09:00:00"
    avail_id = avail_data["id"]

    # 2. List availability
    list_res = await client.get(f"/api/v1/availability?workspace_id={ws_id}", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Add exception block (e.g. Leave next Monday)
    start_leave = datetime.now(timezone.utc) + timedelta(days=7)
    end_leave = start_leave + timedelta(days=1)
    exc_res = await client.post(
        "/api/v1/availability/exceptions",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "start_at": start_leave.isoformat(),
            "end_at": end_leave.isoformat(),
            "exception_type": "leave",
            "reason": "Annual vacation",
        },
    )
    assert exc_res.status_code == 201
    assert exc_res.json()["exception_type"] == "leave"

    # 4. Generate available slots for an interview
    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Candidate", "last_name": "Slots", "email": "slots@cand.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Slots Interview", "duration_minutes": 60},
    )).json()

    future_target_date = (datetime.now(timezone.utc) + timedelta(days=14)).date()
    slots_res = await client.get(
        f"/api/v1/interviews/{itw['id']}/available-slots?date={future_target_date.isoformat()}&timezone=UTC",
        headers=headers,
    )
    assert slots_res.status_code == 200
    slots_data = slots_res.json()
    assert slots_data["duration_minutes"] == 60
    assert len(slots_data["slots"]) > 0

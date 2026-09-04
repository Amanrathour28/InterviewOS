from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_schedule_ready_interview_and_timezone_conversion(client: AsyncClient):
    # 1. Register & setup org + workspace
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "scheduler@interviewos.com", "password": "Password123!", "first_name": "Lead", "last_name": "Scheduler"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "SchedOrg", "initial_workspace_name": "Eng"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Candidate
    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Dennis", "last_name": "Ritchie", "email": "dennis@bell-labs.com"},
    )).json()

    # Interview (60 minutes)
    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "C & Unix Systems Engineering", "duration_minutes": 60},
    )).json()

    # 2. Incomplete interview cannot be scheduled (0 rounds -> 422)
    future_start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
    fail_sched = await client.post(
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": future_start.isoformat(), "timezone": "Asia/Kolkata"},
    )
    assert fail_sched.status_code == 422
    assert "cannot schedule incomplete interview" in fail_sched.json()["detail"].lower()

    # 3. Add valid 60m round and mark interview as READY
    await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds",
        headers=headers,
        json={"name": "C Systems Architecture", "duration_minutes": 60, "sequence": 1},
    )
    ready_res = await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"

    # 4. Invalid timezone string rejected (400)
    invalid_tz_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": future_start.isoformat(), "timezone": "Invalid/Fake_Timezone"},
    )
    assert invalid_tz_res.status_code == 400
    assert "invalid iana timezone" in invalid_tz_res.json()["detail"].lower()

    # 5. Schedule with valid IANA timezone (Asia/Kolkata)
    sched_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": future_start.isoformat(), "timezone": "Asia/Kolkata"},
    )
    assert sched_res.status_code == 201
    sched_data = sched_res.json()
    assert sched_data["timezone"] == "Asia/Kolkata"
    assert sched_data["status"] == "confirmed"

    # Canonical end time must equal start + 60 minutes
    start_dt = datetime.fromisoformat(sched_data["scheduled_start_at"])
    end_dt = datetime.fromisoformat(sched_data["scheduled_end_at"])
    assert (end_dt - start_dt).total_seconds() == 3600

    # 6. Verify interview state transitioned to SCHEDULED
    itw_detail = (await client.get(f"/api/v1/interviews/{itw['id']}", headers=headers)).json()
    assert itw_detail["status"] == "scheduled"


@pytest.mark.asyncio
async def test_reschedule_and_history_audit_trail(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "rescheduler@interviewos.com", "password": "Password123!", "first_name": "Audit", "last_name": "Trail"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "AuditOrg", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Ken", "last_name": "Thompson", "email": "ken@bell-labs.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "B & Plan 9 Interview", "duration_minutes": 45},
    )).json()

    await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds",
        headers=headers,
        json={"name": "Round 1", "duration_minutes": 45, "sequence": 1},
    )
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # Schedule initial session
    day1 = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
    await client.post(
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": day1.isoformat(), "timezone": "America/New_York"},
    )

    # Reschedule to Day 4 with reason
    day2 = (datetime.now(timezone.utc) + timedelta(days=4)).replace(microsecond=0)
    resched_res = await client.patch(
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={
            "scheduled_start_at": day2.isoformat(),
            "timezone": "Europe/London",
            "reason": "Candidate requested later time slot",
        },
    )
    assert resched_res.status_code == 200
    sched = resched_res.json()
    assert sched["timezone"] == "Europe/London"
    assert len(sched["history"]) == 1
    assert sched["history"][0]["previous_timezone"] == "America/New_York"
    assert sched["history"][0]["new_timezone"] == "Europe/London"
    assert sched["history"][0]["reason"] == "Candidate requested later time slot"


@pytest.mark.asyncio
async def test_cancel_schedule_preserves_record_and_reverts_interview_state(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "canceller@interviewos.com", "password": "Password123!", "first_name": "Cancel", "last_name": "Organizer"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "CancelOrg", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Bjarne", "last_name": "Stroustrup", "email": "bjarne@stroustrup.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "C++ Design Loop", "duration_minutes": 45},
    )).json()

    await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds",
        headers=headers,
        json={"name": "OOP & Types", "duration_minutes": 45, "sequence": 1},
    )
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # Schedule
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)
    await client.post(
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": future_time.isoformat(), "timezone": "UTC"},
    )

    # Cancel schedule
    cancel_res = await client.request(
        "DELETE",
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={"cancellation_reason": "Candidate withdrew application"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"
    assert cancel_res.json()["cancellation_reason"] == "Candidate withdrew application"

    # Interview status reverted to READY
    itw_after = (await client.get(f"/api/v1/interviews/{itw['id']}", headers=headers)).json()
    assert itw_after["status"] == "ready"


@pytest.mark.asyncio
async def test_cross_workspace_scheduling_isolation_forbidden(client: AsyncClient):
    # Workspace A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@tenant-a-sched.com", "password": "Password123!", "first_name": "Alice", "last_name": "A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "Org A", "initial_workspace_name": "WS-A"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    cand_a = (await client.post(
        "/api/v1/candidates",
        headers=headers_a,
        json={"workspace_id": ws_a_id, "first_name": "AliceCand", "last_name": "A", "email": "alice.cand@a.com"},
    )).json()

    itw_a = (await client.post(
        "/api/v1/interviews",
        headers=headers_a,
        json={"workspace_id": ws_a_id, "candidate_id": cand_a["id"], "title": "Confidential A Loop", "duration_minutes": 30},
    )).json()

    # Workspace B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@tenant-b-sched.com", "password": "Password123!", "first_name": "Bob", "last_name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Bob attempts to schedule Alice's interview -> 403 Forbidden
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
    cross_sched = await client.post(
        f"/api/v1/interviews/{itw_a['id']}/schedule",
        headers=headers_b,
        json={"scheduled_start_at": future_time.isoformat(), "timezone": "UTC"},
    )
    assert cross_sched.status_code == 403

    # Bob attempts to get Alice's schedule -> 403 Forbidden
    cross_get = await client.get(f"/api/v1/interviews/{itw_a['id']}/schedule", headers=headers_b)
    assert cross_get.status_code == 403

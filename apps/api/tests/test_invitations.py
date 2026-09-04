from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_invitation_lifecycle_and_public_safety(client: AsyncClient):
    # 1. Register & setup
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "inviter@interviewos.com", "password": "Password123!", "first_name": "Invite", "last_name": "Host"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "InviteCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Invite", "last_name": "Candidate", "email": "candidate@external.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "System Architecture Screen", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "R1", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # Schedule session
    start_time = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)
    await client.post(
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": start_time.isoformat(), "timezone": "UTC"},
    )

    # 2. Dispatch invitation
    invite_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/invitations",
        headers=headers,
        json={
            "recipient_type": "candidate",
            "email": "candidate@external.com",
            "recipient_candidate_id": cand["id"],
        },
    )
    assert invite_res.status_code == 201
    invite_data = invite_res.json()
    assert invite_data["email"] == "candidate@external.com"
    assert invite_data["status"] == "sent"

    # 3. Retrieve invitations list
    list_res = await client.get(f"/api/v1/interviews/{itw['id']}/invitations", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


@pytest.mark.asyncio
async def test_notifications_lifecycle(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "notif.user@interviewos.com", "password": "Password123!", "first_name": "Notif", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "NotifCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Jane", "last_name": "Doe", "email": "jane@notif.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Notif Test Interview", "duration_minutes": 45},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "R1", "duration_minutes": 45, "sequence": 1})

    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    await client.post(
        f"/api/v1/interviews/{itw['id']}/participants",
        headers=headers,
        json={"user_id": me["id"], "participant_role": "lead_interviewer", "is_primary": True},
    )
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # Schedule generates notification for participant
    future_time = (datetime.now(timezone.utc) + timedelta(days=6)).replace(microsecond=0)
    await client.post(
        f"/api/v1/interviews/{itw['id']}/schedule",
        headers=headers,
        json={"scheduled_start_at": future_time.isoformat(), "timezone": "UTC"},
    )

    # Fetch notifications
    notifs_res = await client.get("/api/v1/notifications", headers=headers)
    assert notifs_res.status_code == 200
    notifs = notifs_res.json()
    assert len(notifs) >= 1
    target_notif = notifs[0]
    assert "Interview Scheduled" in target_notif["title"]

    # Mark as read
    read_res = await client.patch(f"/api/v1/notifications/{target_notif['id']}/read", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["read_at"] is not None

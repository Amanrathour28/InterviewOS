import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_session_role_based_permissions_and_join_tokens(client: AsyncClient):
    # 1. Interviewer setup
    reg_interviewer = await client.post(
        "/api/v1/auth/register",
        json={"email": "interviewer.sec@interviewos.com", "password": "Password123!", "first_name": "Interviewer", "last_name": "Sec"},
    )
    headers_interviewer = {"Authorization": f"Bearer {reg_interviewer.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers_interviewer, json={"name": "AuthSessionCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 2. Candidate registered account
    reg_candidate = await client.post(
        "/api/v1/auth/register",
        json={"email": "candidate.user@interviewos.com", "password": "Password123!", "first_name": "Candidate", "last_name": "User"},
    )
    headers_candidate = {"Authorization": f"Bearer {reg_candidate.json()['access_token']}"}

    cand_record = (await client.post(
        "/api/v1/candidates",
        headers=headers_interviewer,
        json={"workspace_id": ws_id, "first_name": "Candidate", "last_name": "User", "email": "candidate.user@interviewos.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers_interviewer,
        json={"workspace_id": ws_id, "candidate_id": cand_record["id"], "title": "Secured Interview", "duration_minutes": 45},
    )).json()
    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers_interviewer, json={"name": "R1", "duration_minutes": 45, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers_interviewer, json={"status": "ready"})

    # Create session as interviewer
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers_interviewer)).json()
    sess_id = session["id"]

    # 3. Candidate attempts to start session -> 403 Forbidden
    cand_start = await client.post(f"/api/v1/sessions/{sess_id}/start", headers=headers_candidate)
    assert cand_start.status_code == 403
    assert "interviewer privileges required" in cand_start.json()["detail"].lower()

    # 4. Candidate attempts to pause session -> 403 Forbidden
    cand_pause = await client.post(f"/api/v1/sessions/{sess_id}/pause", headers=headers_candidate)
    assert cand_pause.status_code == 403

    # 5. Candidate attempts to change stage -> 403 Forbidden
    cand_stage = await client.post(
        f"/api/v1/sessions/{sess_id}/stage",
        headers=headers_candidate,
        json={"stage": "coding"},
    )
    assert cand_stage.status_code == 403

    # 6. Candidate attempts to end session -> 403 Forbidden
    cand_end = await client.post(f"/api/v1/sessions/{sess_id}/end", headers=headers_candidate)
    assert cand_end.status_code == 403

    # 7. Unrelated third-party user attempts to access session -> 403 Forbidden
    reg_outsider = await client.post(
        "/api/v1/auth/register",
        json={"email": "outsider@othercorp.com", "password": "Password123!", "first_name": "Outsider", "last_name": "Spy"},
    )
    headers_outsider = {"Authorization": f"Bearer {reg_outsider.json()['access_token']}"}
    outsider_access = await client.get(f"/api/v1/sessions/{sess_id}", headers=headers_outsider)
    assert outsider_access.status_code == 403

    # 8. Interviewer join-token generation
    join_token_res = await client.post(f"/api/v1/sessions/{sess_id}/join-token", headers=headers_interviewer)
    assert join_token_res.status_code == 200
    token_data = join_token_res.json()
    assert token_data["is_interviewer"] is True
    assert token_data["token"] is not None
    assert token_data["room_id"] == f"interview:{sess_id}"
    assert token_data["expires_in_seconds"] == 3600


@pytest.mark.asyncio
async def test_candidate_guest_session_chat_and_coding_isolation(client: AsyncClient):
    # 1. Interviewer setup & instant interview creation
    reg_interviewer = await client.post(
        "/api/v1/auth/register",
        json={"email": "interviewer.guesttest@interviewos.com", "password": "Password123!", "first_name": "Interviewer", "last_name": "GuestTest"},
    )
    headers_interviewer = {"Authorization": f"Bearer {reg_interviewer.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers_interviewer, json={"name": "GuestTestCorp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    instant_res = await client.post(
        "/api/v1/interviews/instant",
        headers=headers_interviewer,
        json={"workspace_id": ws_id, "title": "Guest Session Auth Test", "duration_minutes": 30, "interview_type": "technical"},
    )
    assert instant_res.status_code == 201
    instant_data = instant_res.json()
    raw_token = instant_data["token"]

    # Candidate starts join flow -> gets candidate guest-session token via /identity
    identity_res = await client.post(
        f"/api/v1/interviews/join/{raw_token}/identity",
        json={"name": "Alice Candidate", "email": "alice@test.com"},
    )
    assert identity_res.status_code == 200
    candidate_session_token = identity_res.json()["candidate_session_token"]
    headers_candidate_session = {"Authorization": f"Bearer {candidate_session_token}"}

    # Candidate fetches room session -> gets candidate join token
    room_sess_res = await client.post(
        f"/api/v1/interviews/join/{raw_token}/room-session",
        headers=headers_candidate_session,
    )
    assert room_sess_res.status_code == 200
    room_sess = room_sess_res.json()
    sess_id = room_sess["session_id"]
    candidate_join_token = room_sess["candidate_join_token"]
    headers_candidate_join = {"Authorization": f"Bearer {candidate_join_token}"}

    # 2. Test Chat Permissions:
    # Candidate lists channels -> public is visible, interviewer_private is NOT visible to candidate
    chan_res = await client.get(f"/api/v1/sessions/{sess_id}/chat/channels", headers=headers_candidate_join)
    assert chan_res.status_code == 200
    channels = chan_res.json()
    channel_types = [c["channel_type"] for c in channels]
    assert "public" in channel_types
    assert "interviewer_private" not in channel_types

    public_chan_id = next(c["id"] for c in channels if c["channel_type"] == "public")

    # Candidate can send message to public chat channel
    msg_res = await client.post(
        f"/api/v1/chat/channels/{public_chan_id}/messages",
        headers=headers_candidate_join,
        json={"message_type": "text", "content": "Hello interviewer, I am ready!"},
    )
    assert msg_res.status_code in [200, 201]
    msg_data = msg_res.json()
    assert msg_data["content"] == "Hello interviewer, I am ready!"
    assert msg_data["sender_role"] == "candidate"

    # Interviewer lists channels and finds interviewer_private channel
    int_chan_res = await client.get(f"/api/v1/sessions/{sess_id}/chat/channels", headers=headers_interviewer)
    assert int_chan_res.status_code == 200
    private_chan = next((c for c in int_chan_res.json() if c["channel_type"] == "interviewer_private"), None)

    # Candidate attempts to access interviewer_private channel -> strictly 403 Forbidden
    if private_chan:
        cand_priv_res = await client.get(
            f"/api/v1/chat/channels/{private_chan['id']}/messages",
            headers=headers_candidate_join,
        )
        assert cand_priv_res.status_code == 403

    # 3. Test Coding Permissions:
    # Candidate accesses coding session
    coding_res = await client.get(f"/api/v1/sessions/{sess_id}/coding", headers=headers_candidate_join)
    assert coding_res.status_code == 200
    coding_data = coding_res.json()
    assert "id" in coding_data
    assert "files" in coding_data

    # Candidate updates a file
    if coding_data["files"]:
        file_id = coding_data["files"][0]["id"]
        update_res = await client.patch(
            f"/api/v1/coding/files/{file_id}",
            headers=headers_candidate_join,
            json={"content": "print('candidate code')"},
        )
        assert update_res.status_code == 200

    # Candidate attempts to lock editor -> 401 or 403 Forbidden (interviewer-only operation)
    lock_res = await client.post(
        f"/api/v1/coding/sessions/{coding_data['id']}/lock",
        headers=headers_candidate_join,
        json={"is_locked": True},
    )
    assert lock_res.status_code in [401, 403]


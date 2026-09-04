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

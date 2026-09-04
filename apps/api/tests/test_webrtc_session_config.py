import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webrtc_ice_servers_in_join_token(client: AsyncClient):
    # 1. Setup user, org, candidate, interview
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "webrtc.lead@interviewos.com", "password": "Password123!", "first_name": "WebRTC", "last_name": "Lead"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "WebRTC_Corp", "initial_workspace_name": "WS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Nikola", "last_name": "Tesla", "email": "nikola@tesla.org"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "AC Systems Video Interview", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=headers, json={"name": "Live Video", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=headers, json={"status": "ready"})

    # Create session
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=headers)).json()
    sess_id = session["id"]

    # Request join token
    join_token_res = await client.post(f"/api/v1/sessions/{sess_id}/join-token", headers=headers)
    assert join_token_res.status_code == 200
    data = join_token_res.json()

    # Verify ICE servers list
    assert "ice_servers" in data
    assert isinstance(data["ice_servers"], list)
    assert len(data["ice_servers"]) >= 1
    assert "urls" in data["ice_servers"][0]
    assert "stun" in data["ice_servers"][0]["urls"].lower()

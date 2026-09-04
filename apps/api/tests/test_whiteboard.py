import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_whiteboard_creation_and_session_binding(client: AsyncClient):
    """Test initializing and binding a Whiteboard to an interview session."""
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"wb.lead.{uuid.uuid4().hex[:6]}@interviewos.com",
            "password": "Password123!",
            "first_name": "Lead",
            "last_name": "Interviewer",
        },
    )
    interviewer_headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    org = (await client.post(
        "/api/v1/organizations",
        headers=interviewer_headers,
        json={"name": "WhiteboardOrg", "initial_workspace_name": "SystemDesign"},
    )).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "first_name": "Bob", "last_name": "Candidate", "email": f"bob.{uuid.uuid4().hex[:6]}@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "System Design Architecture", "duration_minutes": 60},
    )).json()

    await client.post(
        f"/api/v1/interviews/{itw['id']}/rounds",
        headers=interviewer_headers,
        json={"name": "Architecture", "duration_minutes": 60, "sequence": 1},
    )
    await client.patch(
        f"/api/v1/interviews/{itw['id']}",
        headers=interviewer_headers,
        json={"status": "ready"},
    )

    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=interviewer_headers)).json()
    sess_id = session["id"]

    # 1. Get or Create Session Whiteboard
    wb_res = await client.get(f"/api/v1/sessions/{sess_id}/whiteboard", headers=interviewer_headers)
    assert wb_res.status_code == 200
    wb_data = wb_res.json()
    assert wb_data["interview_session_id"] == sess_id
    assert wb_data["is_locked"] is False
    assert wb_data["document"] == {}
    wb_id = wb_data["id"]

    # 2. Verify Idempotency on repeated GET
    wb_res2 = await client.get(f"/api/v1/sessions/{sess_id}/whiteboard", headers=interviewer_headers)
    assert wb_res2.status_code == 200
    assert wb_res2.json()["id"] == wb_id


@pytest.mark.asyncio
async def test_whiteboard_patching_and_lock_enforcement(client: AsyncClient):
    """Test updating whiteboard document, locking it, and server-authoritative lock enforcement."""
    # 1. Setup Session
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"lock.lead.{uuid.uuid4().hex[:6]}@interviewos.com", "password": "Password123!", "first_name": "Lock", "last_name": "Lead"},
    )
    interviewer_headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    candidate_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"lock.cand.{uuid.uuid4().hex[:6]}@example.com", "password": "Password123!", "first_name": "Charlie", "last_name": "Candidate"},
    )
    candidate_headers = {"Authorization": f"Bearer {candidate_res.json()['access_token']}"}

    org = (await client.post("/api/v1/organizations", headers=interviewer_headers, json={"name": "LockOrg", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "first_name": "Charlie", "last_name": "Candidate", "email": "lock.cand@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "System Design Lock Test", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=interviewer_headers, json={"name": "Design", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=interviewer_headers, json={"status": "ready"})
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=interviewer_headers)).json()
    sess_id = session["id"]

    wb_res = await client.get(f"/api/v1/sessions/{sess_id}/whiteboard", headers=interviewer_headers)
    wb_id = wb_res.json()["id"]

    # 2. Update whiteboard document as Interviewer
    sample_doc = {
        "shapes": {
            "shape_1": {"type": "rectangle", "x": 100, "y": 100, "label": "API Gateway"},
            "shape_2": {"type": "database", "x": 300, "y": 100, "label": "PostgreSQL"},
        }
    }
    update_res = await client.patch(
        f"/api/v1/whiteboards/{wb_id}",
        json={"document": sample_doc},
        headers=interviewer_headers,
    )
    assert update_res.status_code == 200
    assert "shape_1" in update_res.json()["document"]["shapes"]

    # 3. Lock the whiteboard
    lock_res = await client.post(
        f"/api/v1/whiteboards/{wb_id}/lock",
        json={"is_locked": True},
        headers=interviewer_headers,
    )
    assert lock_res.status_code == 200
    assert lock_res.json()["is_locked"] is True

    # 4. Attempt candidate mutation (without auth / as candidate) -> rejected with 403 Forbidden
    cand_patch = await client.patch(
        f"/api/v1/whiteboards/{wb_id}",
        json={"document": {"shapes": {}}},
    )
    assert cand_patch.status_code == 403
    assert "locked" in cand_patch.json()["detail"].lower()

    # 5. Unlock the whiteboard
    unlock_res = await client.post(
        f"/api/v1/whiteboards/{wb_id}/lock",
        json={"is_locked": False},
        headers=interviewer_headers,
    )
    assert unlock_res.status_code == 200
    assert unlock_res.json()["is_locked"] is False

    # 6. Candidate can edit again after unlock
    cand_patch2 = await client.patch(
        f"/api/v1/whiteboards/{wb_id}",
        json={"document": sample_doc},
    )
    assert cand_patch2.status_code == 200


@pytest.mark.asyncio
async def test_whiteboard_snapshots_and_restore(client: AsyncClient):
    """Test milestone snapshot creation, snapshot listing, and restoring previous states."""
    # 1. Setup Session
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"snap.lead.{uuid.uuid4().hex[:6]}@interviewos.com", "password": "Password123!", "first_name": "Snap", "last_name": "Lead"},
    )
    interviewer_headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    org = (await client.post("/api/v1/organizations", headers=interviewer_headers, json={"name": "SnapOrg", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "first_name": "Dave", "last_name": "Candidate", "email": f"dave.{uuid.uuid4().hex[:6]}@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "System Design Snapshot Test", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=interviewer_headers, json={"name": "Design", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=interviewer_headers, json={"status": "ready"})
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=interviewer_headers)).json()
    sess_id = session["id"]

    wb_res = await client.get(f"/api/v1/sessions/{sess_id}/whiteboard", headers=interviewer_headers)
    wb_id = wb_res.json()["id"]

    # 2. Add Architecture 1
    arch_v1 = {"shapes": {"node1": {"label": "Initial Monolith"}}}
    await client.patch(
        f"/api/v1/whiteboards/{wb_id}",
        json={"document": arch_v1},
        headers=interviewer_headers,
    )

    # 3. Create Milestone Snapshot 1
    snap1_res = await client.post(
        f"/api/v1/whiteboards/{wb_id}/snapshots",
        json={"label": "Initial Monolith Design", "source": "manual"},
        headers=interviewer_headers,
    )
    assert snap1_res.status_code == 200
    snap1_id = snap1_res.json()["id"]
    assert snap1_res.json()["snapshot_number"] == 1
    assert snap1_res.json()["label"] == "Initial Monolith Design"

    # 4. Mutate to Architecture 2
    arch_v2 = {"shapes": {"node1": {"label": "Microservices"}, "node2": {"label": "Kafka Queue"}}}
    await client.patch(
        f"/api/v1/whiteboards/{wb_id}",
        json={"document": arch_v2},
        headers=interviewer_headers,
    )

    # 5. Create Milestone Snapshot 2
    snap2_res = await client.post(
        f"/api/v1/whiteboards/{wb_id}/snapshots",
        json={"label": "Microservices Evolution"},
        headers=interviewer_headers,
    )
    assert snap2_res.status_code == 200
    assert snap2_res.json()["snapshot_number"] == 2

    # 6. List snapshots
    list_snaps = await client.get(
        f"/api/v1/whiteboards/{wb_id}/snapshots",
        headers=interviewer_headers,
    )
    assert list_snaps.status_code == 200
    assert len(list_snaps.json()) == 2

    # 7. Restore Snapshot 1
    restore_res = await client.post(
        f"/api/v1/whiteboards/{wb_id}/snapshots/{snap1_id}/restore",
        headers=interviewer_headers,
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["document"]["shapes"]["node1"]["label"] == "Initial Monolith"


@pytest.mark.asyncio
async def test_private_layer_confidentiality(client: AsyncClient):
    """Test that interviewer private notes and annotations are completely hidden from candidates."""
    # 1. Setup Whiteboard
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": f"priv.lead.{uuid.uuid4().hex[:6]}@interviewos.com", "password": "Password123!", "first_name": "Priv", "last_name": "Lead"},
    )
    interviewer_headers = {"Authorization": f"Bearer {interviewer_res.json()['access_token']}"}

    org = (await client.post("/api/v1/organizations", headers=interviewer_headers, json={"name": "PrivOrg", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "first_name": "Eve", "last_name": "Candidate", "email": f"eve.{uuid.uuid4().hex[:6]}@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "System Design Privacy Test", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=interviewer_headers, json={"name": "Design", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=interviewer_headers, json={"status": "ready"})
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=interviewer_headers)).json()
    sess_id = session["id"]

    wb_res = await client.get(f"/api/v1/sessions/{sess_id}/whiteboard", headers=interviewer_headers)
    wb_id = wb_res.json()["id"]

    # 2. Interviewer saves private notes layer
    private_notes = {"notes": "Candidate forgot to address single point of failure in load balancer."}
    await client.patch(
        f"/api/v1/whiteboards/{wb_id}",
        json={"private_layer": private_notes},
        headers=interviewer_headers,
    )

    # 3. Interviewer gets whiteboard -> private_layer is visible
    interviewer_view = await client.get(
        f"/api/v1/whiteboards/{wb_id}",
        headers=interviewer_headers,
    )
    assert interviewer_view.json()["private_layer"] is not None
    assert "single point of failure" in str(interviewer_view.json()["private_layer"])

    # 4. Register candidate user & get candidate headers
    candidate_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"cand.priv.{uuid.uuid4().hex[:6]}@example.com", "password": "Password123!", "first_name": "Eve", "last_name": "Candidate"},
    )
    candidate_headers = {"Authorization": f"Bearer {candidate_reg.json()['access_token']}"}

    # Candidate gets whiteboard -> private_layer is strictly None
    candidate_view = await client.get(
        f"/api/v1/whiteboards/{wb_id}",
        headers=candidate_headers,
    )
    assert candidate_view.status_code == 200
    assert candidate_view.json()["private_layer"] is None

    # 5. Candidate attempts to inject private layer -> rejected with 403 Forbidden
    candidate_inject = await client.patch(
        f"/api/v1/whiteboards/{wb_id}",
        json={"private_layer": {"malicious": True}},
        headers=candidate_headers,
    )
    assert candidate_inject.status_code == 403

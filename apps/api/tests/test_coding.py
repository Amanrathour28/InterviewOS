import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_coding_session_lifecycle_lock_and_sandbox_execution(client: AsyncClient):
    # 1. Setup Organization, Workspace, Interviewer, Candidate
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "lead.coder@interviewos.com", "password": "Password123!", "first_name": "Lead", "last_name": "Coder"},
    )
    interviewer_token = interviewer_res.json()["access_token"]
    interviewer_headers = {"Authorization": f"Bearer {interviewer_token}"}

    candidate_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice.candidate@example.com", "password": "Password123!", "first_name": "Alice", "last_name": "Candidate"},
    )
    candidate_token = candidate_res.json()["access_token"]
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

    org = (await client.post("/api/v1/organizations", headers=interviewer_headers, json={"name": "CodeOrg", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "first_name": "Alice", "last_name": "Candidate", "email": "alice.candidate@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Senior Algorithms Round", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=interviewer_headers, json={"name": "Coding", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=interviewer_headers, json={"status": "ready"})

    # Create interview session
    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=interviewer_headers)).json()
    sess_id = session["id"]

    # 2. Get or Create Coding Session
    coding_res = await client.get(f"/api/v1/sessions/{sess_id}/coding", headers=interviewer_headers)
    assert coding_res.status_code == 200
    coding_session = coding_res.json()
    assert coding_session["language"] == "python"
    assert len(coding_session["files"]) == 1
    assert coding_session["files"][0]["name"] == "main.py"
    assert coding_session["is_editor_locked"] is False

    coding_sess_id = coding_session["id"]
    main_file_id = coding_session["files"][0]["id"]

    # 3. Candidate Accesses Coding Session
    cand_coding_res = await client.get(f"/api/v1/sessions/{sess_id}/coding", headers=candidate_headers)
    assert cand_coding_res.status_code == 200
    assert cand_coding_res.json()["id"] == coding_sess_id

    # 4. File Operations & Path Traversal Prevention
    # Valid new file
    new_file_res = await client.post(
        f"/api/v1/coding/sessions/{coding_sess_id}/files",
        headers=candidate_headers,
        json={"path": "solution.py", "name": "solution.py", "language": "python", "content": "def add(a, b):\n    return a + b\n"},
    )
    assert new_file_res.status_code == 200
    solution_file = new_file_res.json()
    assert solution_file["path"] == "solution.py"

    # Path traversal attack rejection
    for bad_path in ["../../etc/passwd", "/root/secret", "C:\\Windows\\system.ini", "../main.py"]:
        bad_res = await client.post(
            f"/api/v1/coding/sessions/{coding_sess_id}/files",
            headers=candidate_headers,
            json={"path": bad_path, "name": "evil.py", "language": "python", "content": "malicious"},
        )
        assert bad_res.status_code == 400

    # 5. Editor Locking (Interviewer only)
    # Candidate attempting to lock editor -> 403 Forbidden
    cand_lock_fail = await client.post(
        f"/api/v1/coding/sessions/{coding_sess_id}/lock",
        headers=candidate_headers,
        json={"is_locked": True},
    )
    assert cand_lock_fail.status_code == 403

    # Interviewer locks editor -> 200 OK
    itw_lock_res = await client.post(
        f"/api/v1/coding/sessions/{coding_sess_id}/lock",
        headers=interviewer_headers,
        json={"is_locked": True},
    )
    assert itw_lock_res.status_code == 200
    assert itw_lock_res.json()["is_editor_locked"] is True

    # When locked, candidate cannot create or modify files -> 403 Forbidden
    cand_edit_fail = await client.patch(
        f"/api/v1/coding/files/{solution_file['id']}",
        headers=candidate_headers,
        json={"content": "tampered content"},
    )
    assert cand_edit_fail.status_code == 403

    # Interviewer unlocks editor
    await client.post(
        f"/api/v1/coding/sessions/{coding_sess_id}/lock",
        headers=interviewer_headers,
        json={"is_locked": False},
    )

    # Candidate can edit again
    cand_edit_ok = await client.patch(
        f"/api/v1/coding/files/{solution_file['id']}",
        headers=candidate_headers,
        json={"content": "def add(a, b):\n    return a + b\n"},
    )
    assert cand_edit_ok.status_code == 200

    # 6. Snapshots
    snap_res = await client.post(
        f"/api/v1/coding/sessions/{coding_sess_id}/snapshots",
        headers=candidate_headers,
        json={
            "reason": "manual",
            "files": [{"path": "main.py", "name": "main.py", "language": "python", "content": "print('hello')"}]
        },
    )
    assert snap_res.status_code == 200
    assert snap_res.json()["reason"] == "manual"

    # List snapshots
    snaps_list = await client.get(f"/api/v1/coding/sessions/{coding_sess_id}/snapshots", headers=interviewer_headers)
    assert snaps_list.status_code == 200
    assert len(snaps_list.json()) >= 2  # initial session_start + manual

    # 7. Code Execution & Test Evaluation
    exec_code = """
import sys

def main():
    lines = sys.stdin.read().split()
    if not lines:
        print("42")
        return
    a = int(lines[0])
    b = int(lines[1])
    print(a + b)

if __name__ == "__main__":
    main()
"""
    exec_res = await client.post(
        f"/api/v1/coding/sessions/{coding_sess_id}/execute",
        headers=candidate_headers,
        json={
            "language": "python",
            "files": [{"path": "main.py", "name": "main.py", "language": "python", "content": exec_code}],
            "custom_input": "10 25",
        },
    )
    assert exec_res.status_code == 200
    job = exec_res.json()
    assert job["status"] == "completed"
    assert job["result"]["status"] == "passed"
    assert "35" in job["result"]["stdout"]

    # 8. Standard Execution without custom input
    std_exec = await client.post(
        f"/api/v1/coding/sessions/{coding_sess_id}/execute",
        headers=candidate_headers,
        json={
            "language": "python",
            "files": [{"path": "main.py", "name": "main.py", "language": "python", "content": "print('InterviewOS Sandbox Active!')"}],
        },
    )
    assert std_exec.status_code == 200
    assert "InterviewOS Sandbox Active!" in std_exec.json()["result"]["stdout"]

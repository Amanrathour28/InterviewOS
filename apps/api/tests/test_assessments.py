import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_session_problem_assignment_submission_and_hidden_test_security(client: AsyncClient):
    # 1. Register Interviewer & Organization / Workspace
    interviewer_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "ian.interviewer@example.com", "password": "Password123!", "first_name": "Ian", "last_name": "Interviewer"},
    )
    assert interviewer_res.status_code == 201
    interviewer_token = interviewer_res.json()["access_token"]
    interviewer_headers = {"Authorization": f"Bearer {interviewer_token}"}

    org = (await client.post("/api/v1/organizations", headers=interviewer_headers, json={"name": "AssessCorp", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 2. Register Candidate & create Candidate record + Interview + Session
    candidate_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "charlie.candidate@example.com", "password": "Password123!", "first_name": "Charlie", "last_name": "Candidate"},
    )
    assert candidate_res.status_code == 201
    candidate_token = candidate_res.json()["access_token"]
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

    cand = (await client.post(
        "/api/v1/candidates",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "first_name": "Charlie", "last_name": "Candidate", "email": "charlie.candidate@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=interviewer_headers,
        json={"workspace_id": ws_id, "candidate_id": cand["id"], "title": "Assessment Interview", "duration_minutes": 60},
    )).json()

    await client.post(f"/api/v1/interviews/{itw['id']}/rounds", headers=interviewer_headers, json={"name": "Live Coding", "duration_minutes": 60, "sequence": 1})
    await client.patch(f"/api/v1/interviews/{itw['id']}", headers=interviewer_headers, json={"status": "ready"})

    session = (await client.post(f"/api/v1/interviews/{itw['id']}/session", headers=interviewer_headers)).json()
    sess_id = session["id"]

    # 3. Candidate accesses coding session
    coding_sess = (await client.get(f"/api/v1/sessions/{sess_id}/coding", headers=candidate_headers)).json()
    coding_session_id = coding_sess["id"]

    # 4. Interviewer creates Problem with Public and Hidden test cases
    prob_res = await client.post(
        "/api/v1/coding/problems",
        json={
            "workspace_id": ws_id,
            "title": "Reverse String",
            "difficulty": "easy",
            "category": "strings",
            "starter_codes": {"python": "import sys\nline = sys.stdin.read().strip()\nprint(line[::-1])"},
            "test_cases": [
                {
                    "title": "Public Test: hello",
                    "input_data": "hello",
                    "expected_output": "olleh",
                    "is_hidden": False,
                    "weight": 1.0,
                },
                {
                    "title": "Hidden Test: secret_input_xyz",
                    "input_data": "interviewos",
                    "expected_output": "soweivretni",
                    "is_hidden": True,
                    "weight": 2.0,
                },
            ],
        },
        headers=interviewer_headers,
    )
    assert prob_res.status_code == 201
    problem_id = prob_res.json()["id"]

    # 5. Interviewer assigns problem to session
    assign_res = await client.post(
        f"/api/v1/coding/sessions/{coding_session_id}/problems/assign",
        json={"problem_id": problem_id},
        headers=interviewer_headers,
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "assigned"

    # 6. Candidate submits solution
    submit_res = await client.post(
        f"/api/v1/coding/sessions/{coding_session_id}/problems/submit",
        json={
            "language": "python",
            "files": [{
                "path": "main.py",
                "name": "main.py",
                "language": "python",
                "content": "import sys\nline = sys.stdin.read().strip()\nprint(line[::-1])",
            }],
        },
        headers=candidate_headers,
    )
    assert submit_res.status_code == 200
    sub = submit_res.json()
    assert sub["submission_number"] == 1
    assert sub["total_tests"] == 2
    assert sub["tests_passed"] == 2
    assert sub["score"] == 100.0

    # 7. Verify Candidate Hidden Test Sanitization
    hidden_result = next((tr for tr in sub["test_results"] if tr["is_hidden"]), None)
    assert hidden_result is not None
    assert hidden_result["title"] == "Hidden Test Case"

    # 8. Candidate checks submission history
    history_res = await client.get(
        f"/api/v1/coding/sessions/{coding_session_id}/problems/submissions",
        headers=candidate_headers,
    )
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 1
    assert history[0]["score"] == 100.0

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_problem_library_crud_and_versioning(client: AsyncClient):
    # 1. Register interviewer & create organization/workspace
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice.interviewer@example.com",
            "password": "Password123!",
            "first_name": "Alice",
            "last_name": "Interviewer",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    org_res = await client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": "TechCorp", "initial_workspace_name": "Engineering"},
    )
    assert org_res.status_code == 201
    ws_id = org_res.json()["workspaces"][0]["id"]

    # 2. Create Problem (Version 1)
    create_payload = {
        "workspace_id": ws_id,
        "title": "Two Sum",
        "short_description": "Find two numbers that add up to target.",
        "difficulty": "easy",
        "category": "arrays",
        "estimated_duration_minutes": 25,
        "default_time_limit_seconds": 3.0,
        "default_memory_limit_mb": 256,
        "tags": ["arrays", "hashmap"],
        "is_system": False,
        "problem_statement": "# Two Sum\nGiven an array of integers, return indices...",
        "examples": [{"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]"}],
        "constraints": ["2 <= nums.length <= 10^4"],
        "starter_codes": {
            "python": "def twoSum(nums, target):\n    pass",
            "javascript": "function twoSum(nums, target) {\n}",
        },
        "test_cases": [
            {
                "title": "Public Test 1",
                "input_data": "[2, 7, 11, 15]\n9",
                "expected_output": "[0, 1]",
                "is_hidden": False,
                "weight": 1.0,
            },
            {
                "title": "Hidden Test 1",
                "input_data": "[3, 2, 4]\n6",
                "expected_output": "[1, 2]",
                "is_hidden": True,
                "weight": 2.0,
            },
        ],
    }

    res = await client.post("/api/v1/coding/problems", json=create_payload, headers=headers)
    assert res.status_code == 201
    prob = res.json()
    assert prob["title"] == "Two Sum"
    assert prob["difficulty"] == "easy"
    assert prob["current_version"]["version_number"] == 1
    assert len(prob["current_version"]["test_cases"]) == 2
    problem_id = prob["id"]

    # 3. Update Problem Statement -> Increments Version to 2
    update_payload = {
        "problem_statement": "# Two Sum (Enhanced)\nGiven an array of integers, return indices of the two numbers.",
        "constraints": ["2 <= nums.length <= 10^5"],
    }
    update_res = await client.patch(f"/api/v1/coding/problems/{problem_id}", json=update_payload, headers=headers)
    assert update_res.status_code == 200
    updated_prob = update_res.json()
    assert updated_prob["current_version"]["version_number"] == 2
    assert "Enhanced" in updated_prob["current_version"]["problem_statement"]
    assert updated_prob["versions_count"] == 2
    # Test cases copied over to new version
    assert len(updated_prob["current_version"]["test_cases"]) == 2

    # 4. Clone Problem
    clone_res = await client.post(
        f"/api/v1/coding/problems/{problem_id}/clone",
        json={"new_title": "Two Sum (Custom Variant)"},
        headers=headers,
    )
    assert clone_res.status_code == 201
    cloned_prob = clone_res.json()
    assert cloned_prob["title"] == "Two Sum (Custom Variant)"
    assert cloned_prob["id"] != problem_id

    # 5. Archive Problem
    arch_res = await client.post(f"/api/v1/coding/problems/{problem_id}/archive", headers=headers)
    assert arch_res.status_code == 200
    assert arch_res.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_problem_library_tenant_isolation(client: AsyncClient):
    # Setup Workspace A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "user.a@example.com", "password": "Password123!", "first_name": "User", "last_name": "A"},
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "Org A", "initial_workspace_name": "WS A"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    # Setup Workspace B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "user.b@example.com", "password": "Password123!", "first_name": "User", "last_name": "B"},
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    org_b = (await client.post("/api/v1/organizations", headers=headers_b, json={"name": "Org B", "initial_workspace_name": "WS B"})).json()

    # User A creates problem in WS A
    create_res = await client.post(
        "/api/v1/coding/problems",
        json={
            "workspace_id": ws_a_id,
            "title": "Private Problem A",
            "difficulty": "medium",
            "category": "graphs",
        },
        headers=headers_a,
    )
    assert create_res.status_code == 201
    prob_a_id = create_res.json()["id"]

    # User B from WS B tries to access Problem A -> 404 Not Found
    res_b = await client.get(
        f"/api/v1/coding/problems/{prob_a_id}",
        headers=headers_b,
    )
    assert res_b.status_code == 404

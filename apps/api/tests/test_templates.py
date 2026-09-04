import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_templates(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "tpl@admin.com", "password": "Password123!", "first_name": "Tpl", "last_name": "Admin"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "TplOrg", "initial_workspace_name": "Tech"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 1. Create Template with 2 rounds
    payload = {
        "workspace_id": ws_id,
        "name": "Senior Fullstack Engineer Template",
        "description": "Standard 2-hour interview loop for senior fullstack candidates.",
        "interview_type": "technical",
        "difficulty": "senior",
        "total_duration_minutes": 120,
        "rounds": [
            {
                "name": "Technical Architecture & Systems",
                "round_type": "system_design",
                "sequence": 1,
                "duration_minutes": 60,
                "difficulty": "senior",
                "instructions": "Focus on high-availability web service design.",
            },
            {
                "name": "Live Problem Solving",
                "round_type": "coding",
                "sequence": 2,
                "duration_minutes": 60,
                "difficulty": "senior",
                "instructions": "Implement an in-memory cache with LRU eviction.",
            },
        ],
    }
    create_res = await client.post("/api/v1/interview-templates", headers=headers, json=payload)
    assert create_res.status_code == 201
    tpl_data = create_res.json()
    assert tpl_data["name"] == "Senior Fullstack Engineer Template"
    assert len(tpl_data["rounds"]) == 2
    tpl_id = tpl_data["id"]

    # 2. Get single template
    get_res = await client.get(f"/api/v1/interview-templates/{tpl_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["total_duration_minutes"] == 120

    # 3. List templates
    list_res = await client.get(f"/api/v1/interview-templates?workspace_id={ws_id}", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1


@pytest.mark.asyncio
async def test_cross_workspace_template_access_forbidden(client: AsyncClient):
    # Workspace A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@tpl-a.com", "password": "Password123!", "first_name": "Alice", "last_name": "A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "Org A", "initial_workspace_name": "WS-A"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    tpl_a = (await client.post(
        "/api/v1/interview-templates",
        headers=headers_a,
        json={
            "workspace_id": ws_a_id,
            "name": "Proprietary Hiring Loop",
            "total_duration_minutes": 90,
        },
    )).json()

    # Workspace B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@tpl-b.com", "password": "Password123!", "first_name": "Bob", "last_name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Bob attempts to view Alice's template -> 403 Forbidden
    cross_read = await client.get(f"/api/v1/interview-templates/{tpl_a['id']}", headers=headers_b)
    assert cross_read.status_code == 403

    # Bob attempts to delete Alice's template -> 403 Forbidden
    cross_del = await client.delete(f"/api/v1/interview-templates/{tpl_a['id']}", headers=headers_b)
    assert cross_del.status_code == 403

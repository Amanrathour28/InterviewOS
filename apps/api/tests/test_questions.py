import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_questions(client: AsyncClient):
    # Register & setup org + workspace
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "author@questions.com", "password": "Password123!", "first_name": "Question", "last_name": "Author"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "QCorp", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 1. Create Question
    payload = {
        "workspace_id": ws_id,
        "title": "Design a Distributed Rate Limiter",
        "prompt": "How would you design a rate limiter handling 100k requests/second using Redis or token bucket?",
        "question_type": "system_design",
        "difficulty": "hard",
        "category": "Distributed Systems",
        "expected_duration_minutes": 30,
        "skills": ["Redis", "Distributed Systems", "Concurrency"],
        "topics": ["Rate Limiting", "Token Bucket", "Sliding Window"],
        "evaluation_criteria": ["Mentions clock drift", "Discusses Redis cluster race conditions", "Considers graceful degradation"],
        "hints": ["Consider sliding window log vs sliding window counter", "What happens if Redis dies?"],
    }
    create_res = await client.post("/api/v1/questions", headers=headers, json=payload)
    assert create_res.status_code == 201
    q_data = create_res.json()
    assert q_data["title"] == "Design a Distributed Rate Limiter"
    assert q_data["difficulty"] == "hard"
    q_id = q_data["id"]

    # 2. Get single question
    get_res = await client.get(f"/api/v1/questions/{q_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["category"] == "Distributed Systems"

    # 3. List questions in workspace
    list_res = await client.get(f"/api/v1/questions?workspace_id={ws_id}", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["items"][0]["id"] == q_id


@pytest.mark.asyncio
async def test_question_search_and_filtering(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "filter@questions.com", "password": "Password123!", "first_name": "Filter", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "BankCorp", "initial_workspace_name": "Bank"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Create multiple questions
    await client.post(
        "/api/v1/questions",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Invert Binary Tree",
            "prompt": "Given the root of a binary tree, invert the tree, and return its root.",
            "question_type": "technical",
            "difficulty": "easy",
            "category": "Algorithms",
        },
    )
    await client.post(
        "/api/v1/questions",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Conflict Resolution in Engineering Teams",
            "prompt": "Describe a time when you disagreed with a technical decision made by a peer. How did you resolve it?",
            "question_type": "behavioral",
            "difficulty": "medium",
            "category": "Leadership",
        },
    )

    # Search query
    search_res = await client.get(f"/api/v1/questions?workspace_id={ws_id}&search=Binary", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert search_res.json()["items"][0]["title"] == "Invert Binary Tree"

    # Filter by type
    type_res = await client.get(f"/api/v1/questions?workspace_id={ws_id}&question_type=behavioral", headers=headers)
    assert type_res.status_code == 200
    assert type_res.json()["total"] == 1
    assert type_res.json()["items"][0]["category"] == "Leadership"


@pytest.mark.asyncio
async def test_cross_workspace_question_access_forbidden(client: AsyncClient):
    # Workspace A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@tenant-a.com", "password": "Password123!", "first_name": "Alice", "last_name": "A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "Org A", "initial_workspace_name": "WS-A"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    q_a = (await client.post(
        "/api/v1/questions",
        headers=headers_a,
        json={
            "workspace_id": ws_a_id,
            "title": "Secret Algorithmic Challenge",
            "prompt": "Proprietary internal question for Org A",
        },
    )).json()

    # Workspace B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@tenant-b.com", "password": "Password123!", "first_name": "Bob", "last_name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Bob attempts to read Alice's proprietary question -> 403 Forbidden
    cross_read = await client.get(f"/api/v1/questions/{q_a['id']}", headers=headers_b)
    assert cross_read.status_code == 403

    # Bob attempts to list questions specifying Alice's workspace_id -> 403 Forbidden
    cross_list = await client.get(f"/api/v1/questions?workspace_id={ws_a_id}", headers=headers_b)
    assert cross_list.status_code == 403

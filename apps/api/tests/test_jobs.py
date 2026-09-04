import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_jobs(client: AsyncClient):
    # 1. Register and setup org + workspace
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "recruiter@jobs.com", "password": "Password123!", "first_name": "Job", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "TechCorp", "initial_workspace_name": "Backend"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 2. Create Job
    job_payload = {
        "workspace_id": ws_id,
        "title": "Senior Distributed Systems Engineer",
        "description": "Build high-throughput event-driven microservices in Go and Python.",
        "department": "Infrastructure",
        "location": "Remote - US",
        "employment_type": "full_time",
        "experience_min": 5,
        "experience_max": 10,
        "required_skills": ["Go", "Distributed Systems", "Kubernetes", "PostgreSQL"],
        "preferred_skills": ["gRPC", "Kafka", "AWS"],
        "salary_min": 160000,
        "salary_max": 210000,
        "currency": "USD",
    }
    create_res = await client.post("/api/v1/jobs", headers=headers, json=job_payload)
    assert create_res.status_code == 201
    job_data = create_res.json()
    assert job_data["title"] == "Senior Distributed Systems Engineer"
    assert "slug" in job_data
    assert len(job_data["required_skills"]) == 4

    job_id = job_data["id"]

    # 3. Retrieve single job
    get_res = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Senior Distributed Systems Engineer"

    # 4. List jobs in workspace
    list_res = await client.get(f"/api/v1/jobs?workspace_id={ws_id}", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert len(list_res.json()["items"]) == 1


@pytest.mark.asyncio
async def test_job_search_and_pagination(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "searcher@jobs.com", "password": "Password123!", "first_name": "Search", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "SearchCo", "initial_workspace_name": "Engineering"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Create 3 jobs
    titles = ["Frontend React Engineer", "Lead Data Scientist", "DevOps Cloud Architect"]
    for title in titles:
        await client.post(
            "/api/v1/jobs",
            headers=headers,
            json={
                "workspace_id": ws_id,
                "title": title,
                "description": f"Description for {title}",
            },
        )

    # Search for 'React'
    search_res = await client.get(f"/api/v1/jobs?workspace_id={ws_id}&search=React", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert search_res.json()["items"][0]["title"] == "Frontend React Engineer"

    # Test pagination
    paged_res = await client.get(f"/api/v1/jobs?workspace_id={ws_id}&page=1&page_size=2", headers=headers)
    assert paged_res.status_code == 200
    assert paged_res.json()["page_size"] == 2
    assert paged_res.json()["total"] == 3
    assert paged_res.json()["total_pages"] == 2
    assert len(paged_res.json()["items"]) == 2


@pytest.mark.asyncio
async def test_update_and_archive_job(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "updater@jobs.com", "password": "Password123!", "first_name": "Update", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "UpdateCo", "initial_workspace_name": "Ops"})).json()
    ws_id = org["workspaces"][0]["id"]

    job = (await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"workspace_id": ws_id, "title": "Junior QA"},
    )).json()

    # Update title and status
    patch_res = await client.patch(
        f"/api/v1/jobs/{job['id']}",
        headers=headers,
        json={"title": "Senior QA Automation Engineer", "status": "paused"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Senior QA Automation Engineer"
    assert patch_res.json()["status"] == "paused"

    # Soft delete (archive)
    del_res = await client.delete(f"/api/v1/jobs/{job['id']}", headers=headers)
    assert del_res.status_code == 204

    # Getting deleted job returns 404
    get_res = await client.get(f"/api/v1/jobs/{job['id']}", headers=headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_cross_workspace_job_access_forbidden(client: AsyncClient):
    # Workspace A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@tenant-a.com", "password": "Password123!", "first_name": "Alice", "last_name": "A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "Org A", "initial_workspace_name": "A-WS"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    job_a = (await client.post(
        "/api/v1/jobs",
        headers=headers_a,
        json={"workspace_id": ws_a_id, "title": "Confidential Staff Role"},
    )).json()

    # Workspace B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@tenant-b.com", "password": "Password123!", "first_name": "Bob", "last_name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Bob attempts to view Alice's job -> 403 Forbidden
    cross_read = await client.get(f"/api/v1/jobs/{job_a['id']}", headers=headers_b)
    assert cross_read.status_code == 403
    assert "access denied" in cross_read.json()["detail"].lower()

    # Bob attempts to update Alice's job -> 403 Forbidden
    cross_write = await client.patch(
        f"/api/v1/jobs/{job_a['id']}",
        headers=headers_b,
        json={"title": "Hacked Title"},
    )
    assert cross_write.status_code == 403

    # Bob attempts to list jobs passing Alice's workspace_id -> 403 Forbidden
    cross_list = await client.get(f"/api/v1/jobs?workspace_id={ws_a_id}", headers=headers_b)
    assert cross_list.status_code == 403

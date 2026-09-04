import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_extract_resume_claims_and_profile(client: AsyncClient):
    # 1. Register user & org
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice.recruiter@intel.com", "password": "Password123!", "first_name": "Alice", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "IntelOrg", "initial_workspace_name": "Engineering"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 2. Create a candidate
    cand_resp = await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "first_name": "Alice",
            "last_name": "Architect",
            "email": "alice.arch@example.com",
            "headline": "Staff Distributed Systems Engineer",
        },
    )
    assert cand_resp.status_code == 201
    candidate_id = cand_resp.json()["id"]

    # 3. Upload resume to trigger extraction pipeline
    sample_pdf_bytes = b"%PDF-1.4 Mock PDF Alice Architect Staff Software Engineer Skills: Python, FastAPI, PostgreSQL"
    files = {"file": ("alice_resume.pdf", sample_pdf_bytes, "application/pdf")}

    upload_resp = await client.post(
        f"/api/v1/intelligence/candidates/{candidate_id}/resumes",
        headers=headers,
        files=files,
    )
    assert upload_resp.status_code == 201
    version_data = upload_resp.json()
    assert version_data["version_number"] == 1
    assert version_data["parsing_status"] == "completed"
    version_id = version_data["id"]

    # 4. Get structured profile and claims for version
    intel_resp = await client.get(
        f"/api/v1/intelligence/resumes/{version_id}/intelligence",
        headers=headers,
    )
    assert intel_resp.status_code == 200
    intel_data = intel_resp.json()
    assert len(intel_data["profile"]["skills"]) >= 2
    assert len(intel_data["claims"]) >= 1

    # Verify claim provenance
    claim = intel_data["claims"][0]
    assert "evidence" in claim
    assert claim["category"] in ["backend", "databases", "general"]


@pytest.mark.asyncio
async def test_extract_job_intelligence_and_matching(client: AsyncClient):
    # 1. Register user & org
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob.recruiter@intel.com", "password": "Password123!", "first_name": "Bob", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "MatchOrg", "initial_workspace_name": "Backend"})).json()
    ws_id = org["workspaces"][0]["id"]

    # 2. Create candidate
    cand_resp = await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "first_name": "Bob",
            "last_name": "Coder",
            "email": "bob.coder@example.com",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        },
    )
    assert cand_resp.status_code == 201
    candidate_id = cand_resp.json()["id"]

    # Upload resume for candidate
    files = {"file": ("bob_resume.pdf", b"%PDF-1.4 Bob Coder Backend Engineer", "application/pdf")}
    await client.post(
        f"/api/v1/intelligence/candidates/{candidate_id}/resumes",
        headers=headers,
        files=files,
    )

    # 3. Create Job
    job_resp = await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Senior Python Backend Engineer",
            "description": "We are seeking a Senior Python Engineer with 4+ years experience in FastAPI, PostgreSQL, and AWS.",
            "employment_type": "full_time",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "preferred_skills": ["Docker", "AWS", "Kubernetes"],
            "experience_min": 4,
            "experience_max": 8,
        },
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 4. Extract Job Intelligence
    jd_resp = await client.post(
        f"/api/v1/intelligence/jobs/{job_id}/intelligence",
        headers=headers,
    )
    assert jd_resp.status_code == 200
    job_intel = jd_resp.json()
    assert len(job_intel["requirements"]) >= 2

    # 5. Compute Match
    match_resp = await client.post(
        f"/api/v1/intelligence/jobs/{job_id}/candidates/{candidate_id}/match",
        headers=headers,
    )
    assert match_resp.status_code == 200
    match_data = match_resp.json()
    assert match_data["overall_score"] > 60.0
    assert len(match_data["strengths"]) >= 1

    # 6. Retrieve candidate job match
    get_match = await client.get(
        f"/api/v1/intelligence/jobs/{job_id}/candidates/{candidate_id}/match",
        headers=headers,
    )
    assert get_match.status_code == 200
    assert get_match.json()["overall_score"] == match_data["overall_score"]

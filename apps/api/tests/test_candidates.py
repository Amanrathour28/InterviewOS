import io
import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_candidates(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"recruiter.{uid}@candidates.com", "password": "Password123!", "first_name": "Rec", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": f"HiringInc-{uid}", "initial_workspace_name": "Talent"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand_payload = {
        "workspace_id": ws_id,
        "first_name": "Maya",
        "last_name": "Lin",
        "email": f"maya.lin.{uid}@example.com",
        "phone": "+1 555-0199",
        "location": "San Francisco, CA",
        "headline": "Senior Full-Stack Architect",
        "current_company": "Stripe",
        "current_title": "Staff Software Engineer",
        "experience_years": 8.5,
        "education_summary": "B.S. Computer Science, UC Berkeley",
        "linkedin_url": "https://linkedin.com/in/mayalin",
        "github_url": "https://github.com/mayalin",
        "status": "new",
        "source": "referral",
        "tag_names": ["Backend", "High Concurrency", "Senior"],
    }
    create_res = await client.post("/api/v1/candidates", headers=headers, json=cand_payload)
    assert create_res.status_code == 201
    cand_data = create_res.json()
    assert cand_data["first_name"] == "Maya"
    assert cand_data["email"] == f"maya.lin.{uid}@example.com"
    assert len(cand_data["tags"]) == 3
    cand_id = cand_data["id"]

    # Duplicate email in same workspace is rejected with 409
    dup_res = await client.post("/api/v1/candidates", headers=headers, json=cand_payload)
    assert dup_res.status_code == 409

    # List candidates
    list_res = await client.get(f"/api/v1/candidates?workspace_id={ws_id}", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["items"][0]["id"] == cand_id


@pytest.mark.asyncio
async def test_candidate_search_and_filters(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"filter.{uid}@candidates.com", "password": "Password123!", "first_name": "Filter", "last_name": "User"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": f"FilterCorp-{uid}", "initial_workspace_name": "HR"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Create candidates
    await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "first_name": "Devin",
            "last_name": "Smith",
            "email": f"devin.{uid}@google.com",
            "current_company": "Google",
            "status": "interviewing",
        },
    )
    await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": f"sarah.{uid}@cyberdyne.com",
            "current_company": "Cyberdyne",
            "status": "screening",
        },
    )

    # Search for 'Google'
    search_res = await client.get(f"/api/v1/candidates?workspace_id={ws_id}&search=Google", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert search_res.json()["items"][0]["first_name"] == "Devin"

    # Filter by status
    status_res = await client.get(f"/api/v1/candidates?workspace_id={ws_id}&status=screening", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["total"] == 1
    assert status_res.json()["items"][0]["first_name"] == "Sarah"


@pytest.mark.asyncio
async def test_candidate_job_application_pipeline(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"pipeline.{uid}@corp.com", "password": "Password123!", "first_name": "Pipe", "last_name": "Lead"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": f"PipeCorp-{uid}", "initial_workspace_name": "Main"})).json()
    ws_id = org["workspaces"][0]["id"]

    # Create Job
    job = (await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"workspace_id": ws_id, "title": "Staff Engineer", "department": "Infrastructure"},
    )).json()

    # Create Candidate with Job Association
    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "first_name": "Alex",
            "last_name": "Rivera",
            "email": f"alex.{uid}@domain.com",
            "job_id": job["id"],
        },
    )).json()
    assert len(cand["job_applications"]) == 1
    assert cand["job_applications"][0]["status"] == "new"

    # Move application through pipeline: new -> screening -> interviewing -> offered -> hired
    patch_res = await client.patch(
        f"/api/v1/jobs/{job['id']}/candidates/{cand['id']}",
        headers=headers,
        json={"status": "interviewing"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "interviewing"


@pytest.mark.asyncio
async def test_candidate_notes_and_activity_timeline(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"notes.{uid}@corp.com", "password": "Password123!", "first_name": "Note", "last_name": "Taker"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": f"NotesCorp-{uid}", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Eva", "last_name": "Green", "email": f"eva.{uid}@example.com"},
    )).json()

    # Add Note
    note_res = await client.post(
        f"/api/v1/candidates/{cand['id']}/notes",
        headers=headers,
        json={"content": "Strong background in distributed consensus protocols."},
    )
    assert note_res.status_code == 201
    assert "distributed consensus" in note_res.json()["content"]

    # List Notes
    notes_list = await client.get(f"/api/v1/candidates/{cand['id']}/notes", headers=headers)
    assert notes_list.status_code == 200
    assert len(notes_list.json()) == 1

    # Check Activity Timeline
    activity_res = await client.get(f"/api/v1/candidates/{cand['id']}/activity", headers=headers)
    assert activity_res.status_code == 200
    events = [a["event_type"] for a in activity_res.json()]
    assert "candidate_created" in events
    assert "candidate_note_added" in events


@pytest.mark.asyncio
async def test_candidate_document_upload_and_validation(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"docs.{uid}@corp.com", "password": "Password123!", "first_name": "Doc", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": f"DocsCorp-{uid}", "initial_workspace_name": "DocsWS"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Document", "last_name": "Tester", "email": f"doc.tester.{uid}@example.com"},
    )).json()

    # 1. Invalid MIME type (e.g. text/plain or exe)
    invalid_file = ("bad.exe", b"binary content", "application/x-msdownload")
    bad_upload = await client.post(
        f"/api/v1/candidates/{cand['id']}/documents",
        headers=headers,
        files={"file": invalid_file},
    )
    assert bad_upload.status_code == 415

    # 2. Valid PDF Upload
    pdf_content = b"%PDF-1.4 sample pdf content for resume verification"
    valid_file = ("resume_maya.pdf", pdf_content, "application/pdf")
    upload_res = await client.post(
        f"/api/v1/candidates/{cand['id']}/documents",
        headers=headers,
        files={"file": valid_file},
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    assert doc_data["file_name"] == "resume_maya.pdf"
    assert doc_data["mime_type"] == "application/pdf"
    doc_id = doc_data["id"]

    # 3. List Documents
    doc_list = await client.get(f"/api/v1/candidates/{cand['id']}/documents", headers=headers)
    assert doc_list.status_code == 200
    assert len(doc_list.json()) == 1

    # 4. Download Document
    down_res = await client.get(f"/api/v1/candidates/{cand['id']}/documents/{doc_id}/download", headers=headers)
    assert down_res.status_code == 200
    assert down_res.content == pdf_content

    # 5. Delete Document
    del_doc = await client.delete(f"/api/v1/candidates/{cand['id']}/documents/{doc_id}", headers=headers)
    assert del_doc.status_code == 204


@pytest.mark.asyncio
async def test_cross_workspace_candidate_access_forbidden(client: AsyncClient):
    uid = uuid.uuid4().hex[:6]
    # Workspace A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": f"owner.a.{uid}@tenant-a.com", "password": "Password123!", "first_name": "A", "last_name": "User"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": f"TenantA-{uid}", "initial_workspace_name": "WS-A"})).json()
    ws_a = org_a["workspaces"][0]["id"]

    cand_a = (await client.post(
        "/api/v1/candidates",
        headers=headers_a,
        json={"workspace_id": ws_a, "first_name": "Target", "last_name": "Candidate", "email": f"target.{uid}@domain.com"},
    )).json()

    # Workspace B (Different Organization)
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": f"owner.b.{uid}@tenant-b.com", "password": "Password123!", "first_name": "B", "last_name": "User"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # B attempts to read candidate from Workspace A -> 404/403
    forbidden_get = await client.get(f"/api/v1/candidates/{cand_a['id']}", headers=headers_b)
    assert forbidden_get.status_code in (403, 404)

    # B attempts to patch candidate in Workspace A -> 404/403
    forbidden_patch = await client.patch(
        f"/api/v1/candidates/{cand_a['id']}",
        headers=headers_b,
        json={"headline": "Hacked headline"},
    )
    assert forbidden_patch.status_code in (403, 404)

"""
Tests for Phase 14 Adaptive Interviewer & Real-time Questioning.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transcript_ingestion_and_response_boundaries(client: AsyncClient):
    # 1. Register recruiter and setup workspace
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "transcript.recruiter@intel.com", "password": "Password123!", "first_name": "Trans", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "TransOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Theo", "last_name": "Transcript", "email": "theo@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Theo Adaptive Interview",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
        },
    )).json()

    # Ingest interim transcript (continuing)
    ingest1 = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/transcripts",
        headers=headers,
        json={
            "speaker_role": "candidate",
            "text": "I started by breaking down the",
            "is_final": False,
            "confidence": 0.9,
        },
    )
    assert ingest1.status_code == 201
    assert ingest1.json()["boundary_status"] in ["response_started", "response_continuing"]

    # Ingest final complete thought
    ingest2 = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/transcripts",
        headers=headers,
        json={
            "speaker_role": "candidate",
            "text": "I started by breaking down the monolith into event-driven microservices using RabbitMQ for async communication.",
            "is_final": True,
            "confidence": 0.98,
        },
    )
    assert ingest2.status_code == 201
    assert ingest2.json()["boundary_status"] == "response_complete"

    # Get transcript list
    get_res = await client.get(f"/api/v1/interviews/{itw['id']}/adaptive/transcripts", headers=headers)
    assert get_res.status_code == 200
    assert len(get_res.json()) >= 2


@pytest.mark.asyncio
async def test_adaptive_recommendation_lifecycle_and_stale_invalidation(client: AsyncClient):
    # 1. Setup workspace & candidate
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "lifecycle.recruiter@intel.com", "password": "Password123!", "first_name": "Life", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "LifeOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Lila", "last_name": "Life", "email": "lila@example.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Lila Adaptive Interview",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
        },
    )).json()

    # Generate recommendation 1
    gen1 = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/recommendations/generate",
        headers=headers,
        json={
            "current_question": "How do you manage database connections in production?",
            "candidate_response": "We use PgBouncer in transaction pooling mode with max client connections set to 500.",
            "competency_focus": "PostgreSQL",
            "difficulty": "medium",
        },
    )
    assert gen1.status_code == 201
    rec1 = gen1.json()
    assert rec1["status"] == "generated"
    assert rec1["requires_interviewer_approval"] is True

    # Accept recommendation 1
    accept1 = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/recommendations/{rec1['id']}/accept",
        headers=headers,
    )
    assert accept1.status_code == 200
    assert accept1.json()["status"] == "accepted"

    # Generate recommendation 2
    gen2 = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/recommendations/generate",
        headers=headers,
        json={
            "current_question": "Explain connection pooling caveats.",
            "candidate_response": "Prepared statements can have session affinity issues in transaction pooling.",
            "competency_focus": "PostgreSQL",
        },
    )
    assert gen2.status_code == 201
    rec2 = gen2.json()

    # Edit recommendation 2
    edit2 = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/recommendations/{rec2['id']}/edit",
        headers=headers,
        json={"edited_question": "How specifically do you configure client prepared statements with PgBouncer?"},
    )
    assert edit2.status_code == 200
    assert edit2.json()["status"] == "edited"
    assert "specifically" in edit2.json()["recommended_question"]

    # Verify live coverage updated
    cov = await client.get(f"/api/v1/interviews/{itw['id']}/adaptive/coverage", headers=headers)
    assert cov.status_code == 200
    cov_data = cov.json()
    assert cov_data["total_competencies"] >= 1
    assert any(c["competency"] == "PostgreSQL" for c in cov_data["competencies"])


@pytest.mark.asyncio
async def test_candidate_forbidden_from_interviewer_ai_recommendations(client: AsyncClient):
    # Setup Recruiter
    rec_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "rec.sec@intel.com", "password": "Password123!", "first_name": "Sec", "last_name": "Recruiter"},
    )
    rec_headers = {"Authorization": f"Bearer {rec_reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=rec_headers, json={"name": "SecOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "cand.sec@intel.com", "password": "Password123!", "first_name": "Cand", "last_name": "Sec"},
    )
    cand_headers = {"Authorization": f"Bearer {cand_reg.json()['access_token']}"}

    cand = (await client.post(
        "/api/v1/candidates",
        headers=rec_headers,
        json={"workspace_id": ws_id, "first_name": "Cand", "last_name": "Sec", "email": "cand.sec@intel.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=rec_headers,
        json={
            "workspace_id": ws_id,
            "title": "Security Adaptive Interview",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
        },
    )).json()

    # Candidate attempts to generate/read interviewer recommendations -> MUST BE FORBIDDEN (403)
    hack_gen = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/recommendations/generate",
        headers=cand_headers,
        json={"competency_focus": "System Design"},
    )
    assert hack_gen.status_code == 403

    hack_get = await client.get(
        f"/api/v1/interviews/{itw['id']}/adaptive/recommendations",
        headers=cand_headers,
    )
    assert hack_get.status_code == 403

    hack_cov = await client.get(
        f"/api/v1/interviews/{itw['id']}/adaptive/coverage",
        headers=cand_headers,
    )
    assert hack_cov.status_code == 403

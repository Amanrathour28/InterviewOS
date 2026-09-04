"""
Tests for Phase 14.1 Live Audio Capture, STT Pipeline, and End-to-End Transcription Flow.
"""

import base64
import pytest
from httpx import AsyncClient

from app.services.stt_service import (
    GroqWhisperSTTProvider,
    LocalWhisperSTTProvider,
    MockZeroCostSTTProvider,
    stt_service,
)


@pytest.mark.asyncio
async def test_stt_providers_health_and_capabilities():
    mock_p = MockZeroCostSTTProvider()
    assert (await mock_p.health())["status"] == "ready"
    assert "wav" in mock_p.capabilities()["formats"]

    groq_p = GroqWhisperSTTProvider(api_key="gsk_test_mock_key")
    assert groq_p.capabilities()["realtime_chunking"] is True

    local_p = LocalWhisperSTTProvider()
    assert (await local_p.health())["is_cloud"] is False

    # Test direct transcription on mock provider
    text, conf = await mock_p.transcribe(b"TEST_TRANSCRIPT: I used Redis as a caching layer.", "test.wav")
    assert "Redis" in text
    assert conf > 0.9


@pytest.mark.asyncio
async def test_audio_chunk_transcription_and_boundary_detection(client: AsyncClient):
    # 1. Register recruiter and setup interview
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "stt.recruiter@intel.com", "password": "Password123!", "first_name": "STT", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "STTOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Sam", "last_name": "Speaker", "email": "sam@speaker.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Sam Live Audio Interview",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
        },
    )).json()

    # 2. Check STT health endpoint
    health_res = await client.get(f"/api/v1/interviews/{itw['id']}/adaptive/audio/stt/health", headers=headers)
    assert health_res.status_code == 200
    assert "health" in health_res.json()
    assert "capabilities" in health_res.json()

    # 3. Send candidate audio chunk (Base64)
    simulated_speech = b"RIFF" + b"\x00" * 40 + b"TEST_TRANSCRIPT: We designed the service with idempotency keys to prevent duplicate payments."
    b64_audio = base64.b64encode(simulated_speech).decode("utf-8")

    transcribe_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/audio/transcribe",
        headers=headers,
        json={
            "audio_base64": b64_audio,
            "speaker_role": "candidate",
            "filename": "mic_chunk.wav",
            "start_time_seconds": 0.0,
            "end_time_seconds": 3.5,
            "is_final": True,
        },
    )
    assert transcribe_res.status_code == 201
    data = transcribe_res.json()
    assert "idempotency keys" in data["segment"]["text"]
    assert data["segment"]["speaker_role"] == "candidate"
    assert data["boundary_status"] in ["response_complete", "response_continuing"]

    # 4. Verify segment persisted in interview transcript list
    list_res = await client.get(f"/api/v1/interviews/{itw['id']}/adaptive/transcripts", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert "idempotency keys" in list_res.json()[0]["text"]


@pytest.mark.asyncio
async def test_speaker_attribution_and_crosstalk(client: AsyncClient):
    # Setup interview
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "crosstalk.recruiter@intel.com", "password": "Password123!", "first_name": "Cross", "last_name": "Recruiter"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "CrossOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]

    cand = (await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"workspace_id": ws_id, "first_name": "Chris", "last_name": "Cross", "email": "chris@cross.com"},
    )).json()

    itw = (await client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "workspace_id": ws_id,
            "title": "Crosstalk Interview",
            "candidate_id": cand["id"],
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
        },
    )).json()

    # 1. Interviewer asks question
    q_speech = b"RIFF" + b"\x00" * 40 + b"TEST_TRANSCRIPT: How do you handle schema migrations without downtime?"
    await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/audio/transcribe",
        headers=headers,
        json={
            "audio_base64": base64.b64encode(q_speech).decode("utf-8"),
            "speaker_role": "interviewer",
            "is_final": True,
        },
    )

    # 2. Candidate responds
    ans_speech = b"RIFF" + b"\x00" * 40 + b"TEST_TRANSCRIPT: We use expand and contract pattern with backwards compatible columns."
    ans_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/audio/transcribe",
        headers=headers,
        json={
            "audio_base64": base64.b64encode(ans_speech).decode("utf-8"),
            "speaker_role": "candidate",
            "is_final": True,
        },
    )
    assert ans_res.status_code == 201

    # Verify attribution in transcript list
    segments = (await client.get(f"/api/v1/interviews/{itw['id']}/adaptive/transcripts", headers=headers)).json()
    assert len(segments) == 2
    assert segments[0]["speaker_role"] == "interviewer"
    assert segments[1]["speaker_role"] == "candidate"


@pytest.mark.asyncio
async def test_malformed_and_empty_audio_handling(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "bad.audio@intel.com", "password": "Password123!", "first_name": "Bad", "last_name": "Audio"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    org = (await client.post("/api/v1/organizations", headers=headers, json={"name": "BadOrg", "initial_workspace_name": "Core"})).json()
    ws_id = org["workspaces"][0]["id"]
    cand = (await client.post("/api/v1/candidates", headers=headers, json={"workspace_id": ws_id, "first_name": "B", "last_name": "A", "email": "b@a.com"})).json()
    itw = (await client.post("/api/v1/interviews", headers=headers, json={"workspace_id": ws_id, "title": "Bad Audio", "candidate_id": cand["id"], "scheduled_at": "2026-10-01T10:00:00Z", "duration_minutes": 30})).json()

    # Invalid base64
    inv_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/audio/transcribe",
        headers=headers,
        json={"audio_base64": "not-valid-base64-!!!", "speaker_role": "candidate"},
    )
    assert inv_res.status_code == 400

    # Empty payload
    empty_b64 = base64.b64encode(b"").decode("utf-8")
    empty_res = await client.post(
        f"/api/v1/interviews/{itw['id']}/adaptive/audio/transcribe",
        headers=headers,
        json={"audio_base64": empty_b64, "speaker_role": "candidate"},
    )
    assert empty_res.status_code in [400, 500]

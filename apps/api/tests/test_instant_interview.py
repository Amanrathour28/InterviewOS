"""
tests/test_instant_interview.py — Phase 17.1 regression tests

Covers:
- POST /api/v1/interviews/instant  (create instant interview)
- GET  /api/v1/interviews/join/{token}  (public join info)
- POST /api/v1/interviews/join/{token}/identity  (candidate identity)
- GET  /api/v1/interviews/join/{token}/status    (waiting room poll)
- Guest candidate creation and is_guest flag
- Invitation creation with token hash (no plaintext persisted)
- Candidate session JWT issuance, scope, and expiry
- Cross-interview isolation (candidate A cannot access interview B)
- Unauthorized access to interviewer-only endpoints
- Invalid / expired token handling
"""

import hashlib
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from app.models.candidate import Candidate, CandidateStatus, CandidateSource
from app.models.interview import Interview, InterviewStatus, InterviewType, InterviewDifficulty
from app.models.scheduling import InterviewInvitation, InvitationStatus, RecipientType
from app.models.organization import Organization, OrganizationMembership, OrgMemberRole
from app.models.workspace import Workspace, WorkspaceMembership, WorkspaceMemberRole
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token, create_candidate_session_token, decode_candidate_session_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _create_user_workspace(db, role=UserRole.RECRUITER) -> tuple:
    """Create user → org → workspace → memberships. Returns (user, workspace, org).

    Order matters: Organization.created_by and Workspace.created_by are NOT NULL
    foreign keys to users.id, so the user must exist before the org/workspace.
    """
    tag = uuid.uuid4().hex[:6]

    # Step 1: User first
    user = User(
        email=f"user-{tag}@test.com",
        first_name="Test",
        last_name="User",
        password_hash=hash_password("testpass123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # get user.id before org creation

    # Step 2: Org with created_by
    org = Organization(
        name=f"TestOrg-{tag}",
        slug=f"to-{tag}",
        created_by=user.id,
    )
    db.add(org)
    await db.flush()  # get org.id before workspace creation

    # Step 3: Workspace with created_by
    ws = Workspace(
        organization_id=org.id,
        name=f"TestWS-{tag}",
        slug=f"tw-{tag}",
        created_by=user.id,
    )
    db.add(ws)
    await db.flush()

    org_mem = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=OrgMemberRole.ADMIN,
    )
    db.add(org_mem)

    ws_mem = WorkspaceMembership(
        workspace_id=ws.id,
        user_id=user.id,
        role=WorkspaceMemberRole.INTERVIEWER,
    )
    db.add(ws_mem)
    await db.flush()

    return user, ws, org


def _auth_headers(user_id: str) -> dict:
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/interviews/instant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_instant_interview_success(client: AsyncClient, db_session):
    """Happy path: creates guest candidate, interview, invitation; returns 201."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    payload = {
        "workspace_id": str(ws.id),
        "interview_type": "technical",
        "duration_minutes": 60,
        "candidate_name": "Jane Doe",
        "candidate_email": "jane.doe@example.com",
    }

    resp = await client.post(
        "/api/v1/interviews/instant",
        json=payload,
        headers=_auth_headers(user.id),
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert "interview_id" in data
    assert "token" in data
    assert "join_url" in data
    assert "candidate_id" in data
    assert len(data["token"]) > 20
    assert "/join/" in data["join_url"]


@pytest.mark.asyncio
async def test_create_instant_interview_no_auth_returns_401(client: AsyncClient, db_session):
    """Unauthenticated request must be rejected with 401."""
    resp = await client.post(
        "/api/v1/interviews/instant",
        json={
            "workspace_id": str(uuid.uuid4()),
            "interview_type": "technical",
            "duration_minutes": 60,
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_instant_interview_wrong_workspace_returns_error(client: AsyncClient, db_session):
    """Request for a workspace the user doesn't belong to must fail."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/interviews/instant",
        json={
            "workspace_id": str(uuid.uuid4()),  # random non-existent workspace
            "interview_type": "technical",
            "duration_minutes": 60,
        },
        headers=_auth_headers(user.id),
    )
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_guest_candidate_is_marked_is_guest(client: AsyncClient, db_session):
    """After creation, the candidate record must have is_guest=True."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/interviews/instant",
        json={
            "workspace_id": str(ws.id),
            "interview_type": "coding",
            "duration_minutes": 45,
            "candidate_name": "Ghost User",
        },
        headers=_auth_headers(user.id),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    candidate_id = uuid.UUID(data["candidate_id"])
    result = await db_session.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    assert candidate is not None
    assert candidate.is_guest is True


@pytest.mark.asyncio
async def test_interview_status_is_ready(client: AsyncClient, db_session):
    """Instant interview must be created in READY status (not DRAFT or SCHEDULED)."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/interviews/instant",
        json={
            "workspace_id": str(ws.id),
            "interview_type": "behavioral",
            "duration_minutes": 30,
        },
        headers=_auth_headers(user.id),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    interview_id = uuid.UUID(data["interview_id"])
    result = await db_session.execute(
        select(Interview).where(Interview.id == interview_id)
    )
    interview = result.scalar_one_or_none()
    assert interview is not None
    assert interview.status == InterviewStatus.READY
    assert interview.candidate_id is not None  # candidate_id must remain non-nullable


@pytest.mark.asyncio
async def test_plaintext_token_not_persisted(client: AsyncClient, db_session):
    """The raw join token must NOT be stored in the database — only its SHA-256 hash."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/interviews/instant",
        json={
            "workspace_id": str(ws.id),
            "interview_type": "technical",
            "duration_minutes": 60,
        },
        headers=_auth_headers(user.id),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    raw_token = data["token"]
    interview_id = uuid.UUID(data["interview_id"])

    # Fetch the invitation
    result = await db_session.execute(
        select(InterviewInvitation).where(InterviewInvitation.interview_id == interview_id)
    )
    invitation = result.scalar_one_or_none()
    assert invitation is not None

    # Verify hash is stored, not plaintext
    expected_hash = _sha256(raw_token)
    assert invitation.token_hash == expected_hash
    # The raw token must NOT appear anywhere in the invitation record
    assert raw_token not in (invitation.candidate_name or "")
    assert raw_token not in (invitation.candidate_email or "")


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/interviews/join/{token}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_join_info_valid_token(client: AsyncClient, db_session):
    """Public join info returns 200 for a valid token."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/interviews/instant",
        json={
            "workspace_id": str(ws.id),
            "interview_type": "system_design",
            "duration_minutes": 90,
            "candidate_name": "Alice Smith",
            "candidate_email": "alice@example.com",
        },
        headers=_auth_headers(user.id),
    )
    assert resp.status_code == 201
    token = resp.json()["token"]

    join_resp = await client.get(f"/api/v1/interviews/join/{token}")
    assert join_resp.status_code == 200
    join_data = join_resp.json()

    assert "interview_id" in join_data
    assert "title" in join_data
    assert "interview_type" in join_data
    assert "duration_minutes" in join_data
    assert "status" in join_data
    assert join_data["interview_type"] == "system_design"
    assert join_data["duration_minutes"] == 90


@pytest.mark.asyncio
async def test_get_join_info_invalid_token_returns_404(client: AsyncClient, db_session):
    """A fabricated / invalid token must return 404."""
    resp = await client.get("/api/v1/interviews/join/totally-invalid-token-xyz-abc")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_join_info_expired_token_returns_410(client: AsyncClient, db_session):
    """An expired invitation must return 410 Gone."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    import secrets
    raw_token = secrets.token_urlsafe(32)
    token_hash = _sha256(raw_token)

    # Build a candidate + interview manually so we control expiry
    guest = Candidate(
        workspace_id=ws.id,
        created_by=user.id,
        first_name="Expired",
        last_name="Candidate",
        email="expired@example.com",
        status=CandidateStatus.NEW,
        source=CandidateSource.OTHER,
        is_guest=True,
    )
    db_session.add(guest)
    await db_session.flush()

    interview = Interview(
        workspace_id=ws.id,
        candidate_id=guest.id,
        created_by=user.id,
        title="Expired Interview",
        description="",
        interview_type=InterviewType.TECHNICAL,
        status=InterviewStatus.READY,
        difficulty=InterviewDifficulty.MID,
        duration_minutes=60,
        timezone="UTC",
    )
    db_session.add(interview)
    await db_session.flush()

    expired_invitation = InterviewInvitation(
        interview_id=interview.id,
        workspace_id=ws.id,
        recipient_type=RecipientType.CANDIDATE,
        email="expired@example.com",
        token_hash=token_hash,
        status=InvitationStatus.SENT,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # already expired
        sent_at=datetime.now(timezone.utc) - timedelta(hours=50),
    )
    db_session.add(expired_invitation)
    await db_session.commit()

    resp = await client.get(f"/api/v1/interviews/join/{raw_token}")
    assert resp.status_code == 410


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/interviews/join/{token}/identity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_candidate_identity_issues_session_token(client: AsyncClient, db_session):
    """Candidate identity submission must return a valid candidate session JWT."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/interviews/instant",
        json={
            "workspace_id": str(ws.id),
            "interview_type": "technical",
            "duration_minutes": 60,
        },
        headers=_auth_headers(user.id),
    )
    assert create_resp.status_code == 201
    token = create_resp.json()["token"]
    interview_id = create_resp.json()["interview_id"]

    identity_resp = await client.post(
        f"/api/v1/interviews/join/{token}/identity",
        json={"name": "Bob Builder", "email": "bob@example.com"},
    )
    assert identity_resp.status_code == 200, identity_resp.text
    identity_data = identity_resp.json()

    assert "candidate_session_token" in identity_data
    assert "interview_id" in identity_data
    assert "candidate_name" in identity_data
    assert identity_data["candidate_name"] == "Bob Builder"
    assert str(identity_data["interview_id"]) == interview_id


@pytest.mark.asyncio
async def test_candidate_session_token_has_correct_scope(client: AsyncClient, db_session):
    """Candidate JWT must have type=candidate_session and scope=candidate."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/interviews/instant",
        json={"workspace_id": str(ws.id), "interview_type": "technical", "duration_minutes": 60},
        headers=_auth_headers(user.id),
    )
    assert create_resp.status_code == 201
    token = create_resp.json()["token"]

    identity_resp = await client.post(
        f"/api/v1/interviews/join/{token}/identity",
        json={"name": "Candidate X"},
    )
    assert identity_resp.status_code == 200
    session_token = identity_resp.json()["candidate_session_token"]

    claims = decode_candidate_session_token(session_token)
    assert claims is not None, "Token must be decodable"
    assert claims.get("type") == "candidate_session"
    assert claims.get("scope") == "candidate"
    assert "interview_id" in claims
    assert "invitation_id" in claims


@pytest.mark.asyncio
async def test_candidate_session_token_hash_stored_not_plaintext(client: AsyncClient, db_session):
    """Only the SHA-256 hash of the session token must be persisted."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/interviews/instant",
        json={"workspace_id": str(ws.id), "interview_type": "technical", "duration_minutes": 60},
        headers=_auth_headers(user.id),
    )
    assert create_resp.status_code == 201
    token = create_resp.json()["token"]
    interview_id = uuid.UUID(create_resp.json()["interview_id"])

    identity_resp = await client.post(
        f"/api/v1/interviews/join/{token}/identity",
        json={"name": "Secure Candidate"},
    )
    assert identity_resp.status_code == 200
    session_token = identity_resp.json()["candidate_session_token"]

    result = await db_session.execute(
        select(InterviewInvitation).where(InterviewInvitation.interview_id == interview_id)
    )
    invitation = result.scalar_one_or_none()
    assert invitation is not None
    expected_hash = _sha256(session_token)
    assert invitation.candidate_session_token_hash == expected_hash
    # Plaintext session token must NOT appear in the database record
    assert session_token != invitation.candidate_session_token_hash


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/interviews/join/{token}/status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_waiting_room_status_requires_candidate_session(client: AsyncClient, db_session):
    """Waiting room poll must reject unauthenticated requests with 401."""
    resp = await client.get("/api/v1/interviews/join/some-token/status")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_waiting_room_status_returns_interview_status(client: AsyncClient, db_session):
    """Waiting room poll must return interview status for valid candidate session."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/interviews/instant",
        json={"workspace_id": str(ws.id), "interview_type": "technical", "duration_minutes": 60},
        headers=_auth_headers(user.id),
    )
    assert create_resp.status_code == 201
    token = create_resp.json()["token"]

    identity_resp = await client.post(
        f"/api/v1/interviews/join/{token}/identity",
        json={"name": "Waiter"},
    )
    assert identity_resp.status_code == 200
    session_token = identity_resp.json()["candidate_session_token"]

    status_resp = await client.get(
        f"/api/v1/interviews/join/{token}/status",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "interview_started" in status_data
    assert "interview_status" in status_data
    assert status_data["interview_started"] is False  # not yet started


# ---------------------------------------------------------------------------
# Tests: Security / Cross-interview isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_candidate_cannot_access_different_interview_status(client: AsyncClient, db_session):
    """Candidate A's session token must not grant access to interview B's status endpoint."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    # Create interview A
    resp_a = await client.post(
        "/api/v1/interviews/instant",
        json={"workspace_id": str(ws.id), "interview_type": "technical", "duration_minutes": 60},
        headers=_auth_headers(user.id),
    )
    assert resp_a.status_code == 201
    token_a = resp_a.json()["token"]

    # Create interview B
    resp_b = await client.post(
        "/api/v1/interviews/instant",
        json={"workspace_id": str(ws.id), "interview_type": "coding", "duration_minutes": 45},
        headers=_auth_headers(user.id),
    )
    assert resp_b.status_code == 201
    token_b = resp_b.json()["token"]

    # Get candidate A session
    id_resp = await client.post(
        f"/api/v1/interviews/join/{token_a}/identity",
        json={"name": "Candidate A"},
    )
    assert id_resp.status_code == 200
    session_a = id_resp.json()["candidate_session_token"]

    # Use candidate A's token to access interview B's status — must be denied
    status_resp = await client.get(
        f"/api/v1/interviews/join/{token_b}/status",
        headers={"Authorization": f"Bearer {session_a}"},
    )
    assert status_resp.status_code == 403, (
        "Candidate A should not be able to access interview B's status"
    )


@pytest.mark.asyncio
async def test_candidate_token_rejected_by_interviewer_endpoints(client: AsyncClient, db_session):
    """A candidate session JWT must NOT grant access to interviewer-only endpoints."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/interviews/instant",
        json={"workspace_id": str(ws.id), "interview_type": "technical", "duration_minutes": 60},
        headers=_auth_headers(user.id),
    )
    assert create_resp.status_code == 201
    token = create_resp.json()["token"]

    id_resp = await client.post(
        f"/api/v1/interviews/join/{token}/identity",
        json={"name": "Impersonator"},
    )
    assert id_resp.status_code == 200
    candidate_session = id_resp.json()["candidate_session_token"]

    # Try to create an interview using a candidate session — must fail
    fake_create = await client.post(
        "/api/v1/interviews/instant",
        json={"workspace_id": str(ws.id), "interview_type": "technical", "duration_minutes": 60},
        headers={"Authorization": f"Bearer {candidate_session}"},
    )
    # Must be 401 (token decoded as access token will fail) or 403
    assert fake_create.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_instant_interview_all_types(client: AsyncClient, db_session):
    """All 6 InterviewType values must be accepted by the instant interview endpoint."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    types = ["technical", "coding", "system_design", "behavioral", "mixed", "screening"]
    for itype in types:
        resp = await client.post(
            "/api/v1/interviews/instant",
            json={
                "workspace_id": str(ws.id),
                "interview_type": itype,
                "duration_minutes": 60,
            },
            headers=_auth_headers(user.id),
        )
        assert resp.status_code == 201, f"Failed for type={itype}: {resp.text}"


@pytest.mark.asyncio
async def test_create_instant_interview_without_candidate_info(client: AsyncClient, db_session):
    """Candidate name/email are optional — endpoint must succeed without them."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/interviews/instant",
        json={
            "workspace_id": str(ws.id),
            "interview_type": "technical",
            "duration_minutes": 60,
            # no candidate_name, no candidate_email
        },
        headers=_auth_headers(user.id),
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["candidate_id"] is not None


@pytest.mark.asyncio
async def test_duration_validation(client: AsyncClient, db_session):
    """Duration below 15 or above 480 must be rejected with 422."""
    user, ws, org = await _create_user_workspace(db_session)
    await db_session.commit()

    for bad_duration in [5, 14, 481, 1000]:
        resp = await client.post(
            "/api/v1/interviews/instant",
            json={
                "workspace_id": str(ws.id),
                "interview_type": "technical",
                "duration_minutes": bad_duration,
            },
            headers=_auth_headers(user.id),
        )
        assert resp.status_code == 422, f"Expected 422 for duration={bad_duration}"

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    payload = {
        "email": "sarah.connor@example.com",
        "password": "SecurePassword123!",
        "first_name": "Sarah",
        "last_name": "Connor",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "sarah.connor@example.com"
    assert data["user"]["first_name"] == "Sarah"
    assert data["user"]["last_name"] == "Connor"
    assert data["user"]["role"] == "candidate"


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
        "first_name": "John",
        "last_name": "Doe",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second attempt with same email
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success_and_invalid_password(client: AsyncClient):
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "marcus.vance@example.com",
            "password": "CorrectPassword123!",
            "first_name": "Marcus",
            "last_name": "Vance",
        },
    )

    # Valid Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "marcus.vance@example.com", "password": "CorrectPassword123!"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # Invalid Password
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "marcus.vance@example.com", "password": "WrongPassword999!"},
    )
    assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh_and_rotation(client: AsyncClient):
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alex.morgan@example.com",
            "password": "StrongPassword123!",
            "first_name": "Alex",
            "last_name": "Morgan",
        },
    )
    old_refresh = reg_res.json()["refresh_token"]

    # Refresh
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_res.status_code == 200
    new_refresh = refresh_res.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Using old refresh token must now be rejected (Rotation)
    replay_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert replay_res.status_code == 401


@pytest.mark.asyncio
async def test_get_me_profile_and_change_password(client: AsyncClient):
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "elena.rostova@example.com",
            "password": "InitialPassword123!",
            "first_name": "Elena",
            "last_name": "Rostova",
        },
    )
    access_token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Get profile
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "elena.rostova@example.com"

    # Change password
    change_res = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "InitialPassword123!",
            "new_password": "NewSecretPassword456!",
            "confirm_password": "NewSecretPassword456!",
        },
    )
    assert change_res.status_code == 200

    # Old password no longer works
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "elena.rostova@example.com", "password": "InitialPassword123!"},
    )
    assert old_login.status_code == 401

    # New password succeeds
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "elena.rostova@example.com", "password": "NewSecretPassword456!"},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_session(client: AsyncClient):
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout.user@example.com",
            "password": "Password123!",
            "first_name": "Logout",
            "last_name": "User",
        },
    )
    access_token = reg_res.json()["access_token"]
    refresh_token = reg_res.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Attempting to refresh with revoked token fails
    refresh_attempt = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_attempt.status_code == 401


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow(client: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models.auth import PasswordResetToken

    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "reset.user@example.com",
            "password": "OldPassword123!",
            "first_name": "Reset",
            "last_name": "User",
        },
    )

    # Request forgot password
    forgot_res = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "reset.user@example.com"},
    )
    assert forgot_res.status_code == 200

    # Retrieve reset token from DB directly for testing
    from app.core.security import hash_token
    token_record_stmt = select(PasswordResetToken)
    token_record_res = await db_session.execute(token_record_stmt)
    token_record = token_record_res.scalars().first()
    assert token_record is not None
    assert token_record.is_used is False

    # Simulate resetting with token
    # We can inject a known token into the DB to test the API endpoint
    from app.core.security import generate_secure_token
    known_token = generate_secure_token()
    token_record.token_hash = hash_token(known_token)
    await db_session.commit()

    # Reset password API call
    reset_res = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": known_token,
            "new_password": "CompletelyNewPassword123!",
            "confirm_password": "CompletelyNewPassword123!",
        },
    )
    assert reset_res.status_code == 200

    # Login with new password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset.user@example.com", "password": "CompletelyNewPassword123!"},
    )
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "update.me@example.com", "password": "Password123!", "first_name": "Before", "last_name": "Name"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    update_res = await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"first_name": "After", "display_name": "After N."},
    )
    assert update_res.status_code == 200
    assert update_res.json()["first_name"] == "After"
    assert update_res.json()["display_name"] == "After N."


@pytest.mark.asyncio
async def test_weak_password_rejected(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "short",
            "first_name": "Weak",
            "last_name": "Password",
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(client: AsyncClient, db_session):
    from sqlalchemy import select, update
    from app.models.user import User

    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "banned@example.com",
            "password": "Password123!",
            "first_name": "Banned",
            "last_name": "User",
        },
    )

    # Deactivate user in database
    await db_session.execute(
        update(User).where(User.email == "banned@example.com").values(is_active=False)
    )
    await db_session.commit()

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "banned@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "disabled" in login_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_expired_access_token_rejected(client: AsyncClient):
    from datetime import timedelta
    from app.core.security import create_access_token
    import uuid

    # Create token that expired 1 hour ago
    expired_token = create_access_token(
        subject=str(uuid.uuid4()),
        expires_delta=timedelta(minutes=-60),
    )

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_malformed_and_tampered_jwt_rejected(client: AsyncClient):
    # Malformed token
    res_malformed = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"},
    )
    assert res_malformed.status_code == 401

    # Tampered signature
    from app.core.security import create_access_token
    import uuid
    valid_token = create_access_token(subject=str(uuid.uuid4()))
    parts = valid_token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.tampered_signature_bytes"

    res_tampered = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res_tampered.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_reuse_theft_detection(client: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models.auth import RefreshSession

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "victim@example.com", "password": "Password123!", "first_name": "Victim", "last_name": "User"},
    )
    original_refresh = reg.json()["refresh_token"]

    # Legitimate refresh (old token is now rotated and revoked)
    refresh_1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    assert refresh_1.status_code == 200
    new_refresh = refresh_1.json()["refresh_token"]

    # Adversary replays original_refresh (Replay Attack)
    replay_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    assert replay_res.status_code == 401
    assert "revoked refresh token presented" in replay_res.json()["detail"].lower()

    # Theft detection must have invalidated ALL sessions for victim
    # Attempting to use the new_refresh should now also fail!
    victim_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert victim_refresh.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_token_reuse_rejected(client: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models.auth import PasswordResetToken
    from app.core.security import generate_secure_token, hash_token

    await client.post(
        "/api/v1/auth/register",
        json={"email": "replay.reset@example.com", "password": "OldPassword123!", "first_name": "Replay", "last_name": "Reset"},
    )
    await client.post("/api/v1/auth/forgot-password", json={"email": "replay.reset@example.com"})

    # Setup token
    token_record = (await db_session.execute(select(PasswordResetToken))).scalars().first()
    raw_token = generate_secure_token()
    token_record.token_hash = hash_token(raw_token)
    await db_session.commit()

    # First reset succeeds
    res1 = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "NewPassword123!", "confirm_password": "NewPassword123!"},
    )
    assert res1.status_code == 200

    # Second reset with same token MUST be rejected
    res2 = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "AnotherPassword123!", "confirm_password": "AnotherPassword123!"},
    )
    assert res2.status_code == 400

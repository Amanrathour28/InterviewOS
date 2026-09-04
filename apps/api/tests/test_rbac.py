import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_organization_creation_elevates_owner(client: AsyncClient):
    # Candidate registers
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "candidate.user@example.com",
            "password": "Password123!",
            "first_name": "Dev",
            "last_name": "User",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Create Organization
    org_res = await client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": "Stripe Engineering", "initial_workspace_name": "Core Payments"},
    )
    assert org_res.status_code == 201
    org_data = org_res.json()
    assert org_data["name"] == "Stripe Engineering"
    assert org_data["role"] == "owner"
    assert len(org_data["workspaces"]) == 1
    assert org_data["workspaces"][0]["name"] == "Core Payments"

    # User profile should now show organization membership
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert len(me.json()["organizations"]) == 1
    assert me.json()["role"] == "organization_admin"


@pytest.mark.asyncio
async def test_unauthorized_access_rejected(client: AsyncClient):
    # Missing token
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401

    # Invalid token
    res_bad = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert res_bad.status_code == 401


@pytest.mark.asyncio
async def test_non_admin_cannot_create_workspace(client: AsyncClient, db_session):
    from app.models.organization import OrganizationMembership, OrgMemberRole

    # 1. Register Owner
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@corp.com", "password": "Password123!", "first_name": "Org", "last_name": "Owner"},
    )
    owner_headers = {"Authorization": f"Bearer {owner_reg.json()['access_token']}"}

    org_res = await client.post(
        "/api/v1/organizations",
        headers=owner_headers,
        json={"name": "BigCorp", "initial_workspace_name": "Main"},
    )
    org_id = org_res.json()["id"]

    # 2. Register Candidate / Member
    member_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "member@corp.com", "password": "Password123!", "first_name": "Org", "last_name": "Member"},
    )
    member_id = member_reg.json()["user"]["id"]
    member_headers = {"Authorization": f"Bearer {member_reg.json()['access_token']}"}

    # Add as regular member (not admin)
    import uuid
    membership = OrganizationMembership(
        organization_id=uuid.UUID(org_id),
        user_id=uuid.UUID(member_id),
        role=OrgMemberRole.MEMBER,
    )
    db_session.add(membership)
    await db_session.commit()

    # 3. Regular member attempts to create workspace -> 403 Forbidden
    create_ws = await client.post(
        "/api/v1/workspaces",
        headers=member_headers,
        json={"organization_id": org_id, "name": "Unauthorized Lab"},
    )
    assert create_ws.status_code == 403
    assert "admin privileges required" in create_ws.json()["detail"].lower()

    # 4. Owner can create workspace -> 201 Created
    owner_create_ws = await client.post(
        "/api/v1/workspaces",
        headers=owner_headers,
        json={"organization_id": org_id, "name": "Authorized Lab"},
    )
    assert owner_create_ws.status_code == 201


@pytest.mark.asyncio
async def test_cross_workspace_access_rejected(client: AsyncClient):
    # Org A Owner
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@org-a.com", "password": "Password123!", "first_name": "Alice", "last_name": "A"},
    )
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}
    org_a = (await client.post("/api/v1/organizations", headers=headers_a, json={"name": "Org A", "initial_workspace_name": "A-WS"})).json()
    ws_a_id = org_a["workspaces"][0]["id"]

    # Org B Owner
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@org-b.com", "password": "Password123!", "first_name": "Bob", "last_name": "B"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Bob attempts to access Alice's workspace directly -> 403 Forbidden
    cross_ws_res = await client.get(f"/api/v1/workspaces/{ws_a_id}", headers=headers_b)
    assert cross_ws_res.status_code == 403
    assert "access denied" in cross_ws_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rate_limiter_blocks_abuse(client: AsyncClient):
    # Rate limit on login is 5 per minute
    email = "ratelimit.test@example.com"
    pwd = "WrongPassword123!"

    # Execute 6 rapid invalid login requests
    responses = []
    for _ in range(6):
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        responses.append(res.status_code)

    # At least the 6th request must have been rate-limited with 429
    assert 429 in responses


@pytest.mark.asyncio
async def test_platform_admin_bypass(client: AsyncClient, db_session):
    from sqlalchemy import update
    from app.models.user import User, UserRole

    # Register user
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "superadmin@platform.com", "password": "Password123!", "first_name": "Super", "last_name": "Admin"},
    )
    user_id = reg.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Elevate to PLATFORM_ADMIN in database
    import uuid
    await db_session.execute(
        update(User).where(User.id == uuid.UUID(user_id)).values(role=UserRole.PLATFORM_ADMIN)
    )
    await db_session.commit()

    # Create Org as ordinary user
    other = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@company.com", "password": "Password123!", "first_name": "Other", "last_name": "Company"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    other_org = (await client.post("/api/v1/organizations", headers=other_headers, json={"name": "Private Org", "initial_workspace_name": "Private WS"})).json()
    private_ws_id = other_org["workspaces"][0]["id"]

    # Platform Admin can view workspace even without explicit tenant membership
    admin_access = await client.get(f"/api/v1/workspaces/{private_ws_id}", headers=headers)
    assert admin_access.status_code == 200
    assert admin_access.json()["name"] == "Private WS"

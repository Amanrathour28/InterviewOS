import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_isolation_cross_organization_access_forbidden(client: AsyncClient):
    """
    MANDATORY TENANT ISOLATION TEST:
    Explicitly verifies that User A (belonging to Org A) is strictly forbidden
    from reading, listing, or creating resources inside Org B, even if Org B's
    IDs are manually supplied in API requests.
    """
    # 1. Setup User A and Organization A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@org-a.com",
            "password": "Password123!",
            "first_name": "Alice",
            "last_name": "OrgA",
        },
    )
    headers_a = {"Authorization": f"Bearer {res_a.json()['access_token']}"}

    org_a_res = await client.post(
        "/api/v1/organizations",
        headers=headers_a,
        json={"name": "Acme Corp", "initial_workspace_name": "Acme Main"},
    )
    org_a_id = org_a_res.json()["id"]

    # 2. Setup User B and Organization B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@org-b.com",
            "password": "Password123!",
            "first_name": "Bob",
            "last_name": "OrgB",
        },
    )
    headers_b = {"Authorization": f"Bearer {res_b.json()['access_token']}"}

    org_b_res = await client.post(
        "/api/v1/organizations",
        headers=headers_b,
        json={"name": "Beta Labs", "initial_workspace_name": "Beta Core"},
    )
    org_b_id = org_b_res.json()["id"]
    org_b_ws_id = org_b_res.json()["workspaces"][0]["id"]

    # 3. User A attempts to read Organization B details -> MUST BE FORBIDDEN (403)
    hack_org = await client.get(f"/api/v1/organizations/{org_b_id}", headers=headers_a)
    assert hack_org.status_code == 403
    assert "Access denied" in hack_org.json()["detail"]

    # 4. User A attempts to list Workspaces belonging to Organization B -> MUST BE FORBIDDEN (403)
    hack_workspaces = await client.get(
        f"/api/v1/workspaces?organization_id={org_b_id}",
        headers=headers_a,
    )
    assert hack_workspaces.status_code == 403
    assert "Access denied" in hack_workspaces.json()["detail"]

    # 5. User A attempts to access Organization B's specific workspace directly by ID -> MUST BE FORBIDDEN (403)
    hack_ws = await client.get(
        f"/api/v1/workspaces/{org_b_ws_id}",
        headers=headers_a,
    )
    assert hack_ws.status_code == 403

    # 6. User A attempts to create a workspace inside Organization B -> MUST BE FORBIDDEN (403)
    hack_create_ws = await client.post(
        "/api/v1/workspaces",
        headers=headers_a,
        json={
            "organization_id": org_b_id,
            "name": "Malicious Workspace Injection",
        },
    )
    assert hack_create_ws.status_code == 403

    # 7. Verify legitimate access works for the authorized owner User B
    legit_org = await client.get(f"/api/v1/organizations/{org_b_id}", headers=headers_b)
    assert legit_org.status_code == 200
    assert legit_org.json()["name"] == "Beta Labs"

    legit_ws = await client.get(f"/api/v1/workspaces/{org_b_ws_id}", headers=headers_b)
    assert legit_ws.status_code == 200
    assert legit_ws.json()["name"] == "Beta Core"

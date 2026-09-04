import re
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, verify_org_access
from app.core.database import get_db
from app.models.organization import Organization, OrganizationMembership, OrgMemberRole
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMembership, WorkspaceMemberRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationWithWorkspacesResponse,
    WorkspaceSummary,
)

router = APIRouter()


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


@router.get(
    "",
    response_model=List[OrganizationWithWorkspacesResponse],
    summary="List organizations the authenticated user belongs to",
)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == current_user.id)
        .options(
            selectinload(OrganizationMembership.organization).selectinload(
                Organization.workspaces
            )
        )
    )
    res = await db.execute(stmt)
    memberships = res.scalars().all()

    results = []
    for m in memberships:
        org = m.organization
        if org.is_deleted:
            continue

        workspaces = [
            WorkspaceSummary(
                id=ws.id,
                name=ws.name,
                slug=ws.slug,
            )
            for ws in org.workspaces
            if not ws.is_deleted
        ]

        results.append(
            OrganizationWithWorkspacesResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                logo_url=org.logo_url,
                created_at=org.created_at,
                role=m.role,
                workspaces=workspaces,
            )
        )
    return results


@router.post(
    "",
    response_model=OrganizationWithWorkspacesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization, default workspace, and owner membership",
)
async def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_slug = payload.slug or _slugify(payload.name)
    if not base_slug:
        base_slug = f"org-{uuid.uuid4().hex[:8]}"

    # Ensure unique slug
    candidate_slug = base_slug
    suffix = 1
    while True:
        check_stmt = select(Organization).where(Organization.slug == candidate_slug)
        check_res = await db.execute(check_stmt)
        if not check_res.scalar_one_or_none():
            break
        candidate_slug = f"{base_slug}-{suffix}"
        suffix += 1

    # Atomic creation in transaction
    new_org = Organization(
        name=payload.name.strip(),
        slug=candidate_slug,
        logo_url=payload.logo_url,
        created_by=current_user.id,
    )
    db.add(new_org)
    await db.flush()

    # Create Owner membership
    org_membership = OrganizationMembership(
        organization_id=new_org.id,
        user_id=current_user.id,
        role=OrgMemberRole.OWNER,
    )
    db.add(org_membership)

    # Automatically provision default workspace
    ws_name = payload.initial_workspace_name or "Engineering"
    default_ws = Workspace(
        organization_id=new_org.id,
        name=ws_name,
        slug=_slugify(ws_name) or "default",
        description=f"Primary technical interview workspace for {new_org.name}",
        created_by=current_user.id,
    )
    db.add(default_ws)
    await db.flush()

    # Add workspace admin membership
    ws_membership = WorkspaceMembership(
        workspace_id=default_ws.id,
        user_id=current_user.id,
        role=WorkspaceMemberRole.ADMIN,
    )
    db.add(ws_membership)

    # Elevate user's global role if candidate
    if current_user.role == UserRole.CANDIDATE:
        current_user.role = UserRole.ORGANIZATION_ADMIN

    await db.commit()
    await db.refresh(new_org)

    return OrganizationWithWorkspacesResponse(
        id=new_org.id,
        name=new_org.name,
        slug=new_org.slug,
        logo_url=new_org.logo_url,
        created_at=new_org.created_at,
        role=OrgMemberRole.OWNER,
        workspaces=[
            WorkspaceSummary(
                id=default_ws.id,
                name=default_ws.name,
                slug=default_ws.slug,
                role=WorkspaceMemberRole.ADMIN.value,
            )
        ],
    )


@router.get(
    "/{org_id}",
    response_model=OrganizationWithWorkspacesResponse,
    summary="Get single organization with tenant access verification",
)
async def get_organization(
    org_id: uuid.UUID,
    membership: OrganizationMembership = Depends(verify_org_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Organization)
        .where(Organization.id == org_id, Organization.is_deleted.is_(False))
        .options(selectinload(Organization.workspaces))
    )
    res = await db.execute(stmt)
    org = res.scalar_one()

    workspaces = [
        WorkspaceSummary(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
        )
        for ws in org.workspaces
        if not ws.is_deleted
    ]

    return OrganizationWithWorkspacesResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        created_at=org.created_at,
        role=membership.role if membership else OrgMemberRole.OWNER,
        workspaces=workspaces,
    )

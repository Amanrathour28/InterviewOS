import re
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_org_access, verify_org_admin, verify_workspace_access
from app.core.database import get_db
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership, WorkspaceMemberRole
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter()


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    summary="List workspaces for a verified organization",
)
async def list_workspaces(
    organization_id: uuid.UUID = Query(..., description="Organization ID to list workspaces from"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Strict Tenant Isolation: User MUST be member of the organization
    await verify_org_access(organization_id, current_user, db)

    stmt = (
        select(Workspace, WorkspaceMembership.role)
        .outerjoin(
            WorkspaceMembership,
            (WorkspaceMembership.workspace_id == Workspace.id)
            & (WorkspaceMembership.user_id == current_user.id),
        )
        .where(
            Workspace.organization_id == organization_id,
            Workspace.is_deleted.is_(False),
        )
    )
    res = await db.execute(stmt)
    rows = res.all()

    return [
        WorkspaceResponse(
            id=ws.id,
            organization_id=ws.organization_id,
            name=ws.name,
            slug=ws.slug,
            description=ws.description,
            created_at=ws.created_at,
            role=role,
        )
        for ws, role in rows
    ]


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace within an organization",
)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Tenant Isolation & RBAC: User must be admin/owner of target organization
    await verify_org_admin(payload.organization_id, current_user, db)

    base_slug = payload.slug or _slugify(payload.name)
    if not base_slug:
        base_slug = f"ws-{uuid.uuid4().hex[:8]}"

    # Verify uniqueness within organization
    check_stmt = select(Workspace).where(
        Workspace.organization_id == payload.organization_id,
        Workspace.slug == base_slug,
        Workspace.is_deleted.is_(False),
    )
    check_res = await db.execute(check_stmt)
    if check_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A workspace with slug '{base_slug}' already exists in this organization",
        )

    new_workspace = Workspace(
        organization_id=payload.organization_id,
        name=payload.name.strip(),
        slug=base_slug,
        description=payload.description,
        created_by=current_user.id,
    )
    db.add(new_workspace)
    await db.flush()

    # Automatically add creator as Workspace Admin
    ws_membership = WorkspaceMembership(
        workspace_id=new_workspace.id,
        user_id=current_user.id,
        role=WorkspaceMemberRole.ADMIN,
    )
    db.add(ws_membership)
    await db.commit()
    await db.refresh(new_workspace)

    return WorkspaceResponse(
        id=new_workspace.id,
        organization_id=new_workspace.organization_id,
        name=new_workspace.name,
        slug=new_workspace.slug,
        description=new_workspace.description,
        created_at=new_workspace.created_at,
        role=WorkspaceMemberRole.ADMIN,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get single workspace details with tenant verification",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(verify_workspace_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.is_deleted.is_(False))
    res = await db.execute(stmt)
    ws = res.scalar_one()

    return WorkspaceResponse(
        id=ws.id,
        organization_id=ws.organization_id,
        name=ws.name,
        slug=ws.slug,
        description=ws.description,
        created_at=ws.created_at,
        role=membership.role if membership else WorkspaceMemberRole.ADMIN,
    )

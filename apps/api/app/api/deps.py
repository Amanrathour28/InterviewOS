import uuid
from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token, decode_candidate_session_token
from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationMembership, OrgMemberRole
from app.models.workspace import Workspace, WorkspaceMembership, WorkspaceMemberRole
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.interview import Interview, Question, InterviewTemplate

# Security scheme for Bearer token extraction
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current authenticated user from Bearer header or cookie."""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to HTTP-only cookie if available
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims",
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format",
        )

    stmt = select(User).where(User.id == user_uuid, User.is_deleted.is_(False))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account has been deactivated",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been disabled",
        )

    return user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract authenticated user if present, otherwise return None without raising 401."""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        return None

    stmt = select(User).where(User.id == user_uuid, User.is_deleted.is_(False))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory restricting access to users with specific roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Platform admin always has superuser bypass
        if current_user.role == UserRole.PLATFORM_ADMIN:
            return current_user

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{current_user.role.value}'",
            )
        return current_user

    return role_checker


async def verify_org_access(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMembership:
    """Ensures current user is a valid member of the requested organization (Strict Tenant Isolation)."""
    # Check if organization exists and is not deleted
    org_stmt = select(Organization).where(Organization.id == org_id, Organization.is_deleted.is_(False))
    org_res = await db.execute(org_stmt)
    if not org_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Check membership
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == org_id,
        OrganizationMembership.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    membership = res.scalar_one_or_none()

    if not membership and current_user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this organization",
        )

    return membership


async def verify_org_admin(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMembership:
    """Ensures user has Owner or Admin role in the specified organization."""
    membership = await verify_org_access(org_id, current_user, db)
    if membership and membership.role not in [OrgMemberRole.OWNER, OrgMemberRole.ADMIN]:
        if current_user.role != UserRole.PLATFORM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization admin privileges required",
            )
    return membership


async def verify_workspace_access(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMembership:
    """Ensures current user is a member of the workspace (Strict Tenant Isolation)."""
    ws_stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.is_deleted.is_(False))
    ws_res = await db.execute(ws_stmt)
    workspace = ws_res.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # First verify user has access to parent organization
    await verify_org_access(workspace.organization_id, current_user, db)

    # Check workspace membership
    stmt = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    membership = res.scalar_one_or_none()

    if not membership and current_user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this workspace",
        )

    return membership


async def verify_job_access(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Job:
    """Verifies that the requested job exists and that the user belongs to its parent workspace."""
    stmt = select(Job).where(Job.id == job_id, Job.is_deleted.is_(False))
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Strict Tenant Isolation: user must be an authorized member of job's workspace
    await verify_workspace_access(job.workspace_id, current_user, db)
    return job


async def verify_candidate_access(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    """Verifies that the requested candidate exists and that the user belongs to its parent workspace."""
    stmt = select(Candidate).where(Candidate.id == candidate_id, Candidate.is_deleted.is_(False))
    res = await db.execute(stmt)
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Strict Tenant Isolation: user must be an authorized member of candidate's workspace
    await verify_workspace_access(candidate.workspace_id, current_user, db)
    return candidate


def require_workspace_roles(*allowed_roles: WorkspaceMemberRole):
    """Dependency factory ensuring user has one of the allowed roles within the target workspace."""
    async def _checker(
        workspace_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> WorkspaceMembership:
        membership = await verify_workspace_access(workspace_id, current_user, db)
        if current_user.role == UserRole.PLATFORM_ADMIN:
            return membership

        if not membership or membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following workspace roles: {[r.value for r in allowed_roles]}",
            )
        return membership

    return _checker


async def verify_interview_access(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Interview:
    """Verifies that the requested interview exists and user belongs to its parent workspace."""
    stmt = select(Interview).where(Interview.id == interview_id, Interview.is_deleted.is_(False))
    res = await db.execute(stmt)
    interview = res.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    await verify_workspace_access(interview.workspace_id, current_user, db)
    return interview


async def verify_question_access(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Question:
    """Verifies that the question exists and user has access (workspace member or global system question)."""
    stmt = select(Question).where(Question.id == question_id, Question.is_deleted.is_(False))
    res = await db.execute(stmt)
    question = res.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if question.workspace_id is not None:
        await verify_workspace_access(question.workspace_id, current_user, db)
    return question


async def verify_template_access(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewTemplate:
    """Verifies that the template exists and user has access (workspace member or global system template)."""
    stmt = select(InterviewTemplate).where(InterviewTemplate.id == template_id, InterviewTemplate.is_deleted.is_(False))
    res = await db.execute(stmt)
    template = res.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview template not found")

    if template.workspace_id is not None:
        await verify_workspace_access(template.workspace_id, current_user, db)
    return template


async def get_candidate_session(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Extract and validate a candidate session JWT.

    Returns the decoded claims dict containing:
        scope, invitation_id, interview_id, candidate_name, sub, exp

    This dependency CANNOT satisfy get_current_user — candidate tokens have
    type='candidate_session' which is rejected by decode_access_token.
    """
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("candidate_session")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Candidate session credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_candidate_session_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired candidate session",
        )

    if payload.get("scope") != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient scope",
        )

    return payload



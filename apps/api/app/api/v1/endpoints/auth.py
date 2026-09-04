import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth import PasswordResetToken, RefreshSession
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import MembershipSummary, UserCreate, UserUpdate, UserProfileResponse, UserResponse
from app.api.deps import get_current_user
from app.core.rate_limit import RateLimiter

logger = logging.getLogger("interviewos.auth")
router = APIRouter()


async def _build_token_response(
    user: User,
    request: Request,
    response: Response,
    db: AsyncSession,
    remember_me: bool = False,
) -> TokenResponse:
    """Helper to generate JWT access token and persist a hashed refresh session."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "role": user.role.value},
        expires_delta=access_token_expires,
    )

    # Refresh token configuration
    refresh_days = settings.REFRESH_TOKEN_EXPIRE_DAYS if remember_me else 1
    raw_refresh_token = generate_secure_token()
    token_hashed = hash_token(raw_refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=refresh_days)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:512]

    # Persist session
    session = RefreshSession(
        user_id=user.id,
        token_hash=token_hashed,
        ip_address=client_ip,
        user_agent=user_agent,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(session)
    await db.commit()

    # Set secure HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=not settings.DEBUG,
    )
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        max_age=refresh_days * 86400,
        samesite="lax",
        secure=not settings.DEBUG,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(times=5, seconds=60, prefix="rl:reg")),
):
    normalized_email = payload.email.lower().strip()

    # Check for existing user
    stmt = select(User).where(User.email == normalized_email, User.is_deleted.is_(False))
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        )

    # Password strength check
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long",
        )

    # Hash password with Argon2id
    hashed_pwd = hash_password(payload.password)

    new_user = User(
        email=normalized_email,
        password_hash=hashed_pwd,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        display_name=payload.display_name or f"{payload.first_name} {payload.last_name}".strip(),
        avatar_url=payload.avatar_url,
        role=payload.role or "candidate",
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info("New user registered: %s (id: %s)", new_user.email, new_user.id)
    return await _build_token_response(new_user, request, response, db)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive tokens",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(times=5, seconds=60, prefix="rl:login")),
):
    normalized_email = payload.email.lower().strip()

    stmt = select(User).where(User.email == normalized_email, User.is_deleted.is_(False))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Please contact support.",
        )

    logger.info("User logged in: %s", user.email)
    return await _build_token_response(
        user, request, response, db, remember_me=bool(payload.remember_me)
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and get a new access token",
)
async def refresh_tokens(
    payload: Optional[RefreshTokenRequest] = None,
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    # Support token in body or HTTP cookie
    token_str = None
    if payload and payload.refresh_token:
        token_str = payload.refresh_token
    elif request:
        token_str = request.cookies.get("refresh_token")

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    token_hash = hash_token(token_str)
    now = datetime.now(timezone.utc)

    # Query session by token_hash
    stmt = (
        select(RefreshSession)
        .where(RefreshSession.token_hash == token_hash)
        .options(selectinload(RefreshSession.user))
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    # Replay of revoked token indicates potential token theft
    if session and session.is_revoked:
        logger.warning(
            "REFRESH_TOKEN_REUSE_DETECTED: Attempted reuse of revoked token for user %s. Invalidating all user sessions.",
            session.user_id,
        )
        revoke_all = (
            update(RefreshSession)
            .where(RefreshSession.user_id == session.user_id)
            .values(is_revoked=True)
        )
        await db.execute(revoke_all)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Revoked refresh token presented. All active sessions have been invalidated for security.",
        )

    session_expires = None
    if session and session.expires_at:
        session_expires = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)

    if not session or not session_expires or session_expires <= now or not session.user or not session.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked refresh token",
        )

    # Revoke old session (Refresh Token Rotation)
    session.is_revoked = True
    await db.commit()

    return await _build_token_response(session.user, request, response, db)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke refresh token and logout",
)
async def logout(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token_str = payload.refresh_token if payload else request.cookies.get("refresh_token")
    if token_str:
        token_hash = hash_token(token_str)
        stmt = (
            update(RefreshSession)
            .where(RefreshSession.token_hash == token_hash)
            .values(is_revoked=True)
        )
        await db.execute(stmt)
        await db.commit()

    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile and tenant memberships",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Fetch user's organizations
    org_stmt = (
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == current_user.id)
        .options(selectinload(OrganizationMembership.organization))
    )
    org_res = await db.execute(org_stmt)
    org_memberships = org_res.scalars().all()

    org_summaries = [
        MembershipSummary(
            id=m.id,
            target_id=m.organization.id,
            name=m.organization.name,
            slug=m.organization.slug,
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
        )
        for m in org_memberships
        if not m.organization.is_deleted
    ]

    # Fetch user's workspaces
    ws_stmt = (
        select(WorkspaceMembership)
        .where(WorkspaceMembership.user_id == current_user.id)
        .options(selectinload(WorkspaceMembership.workspace))
    )
    ws_res = await db.execute(ws_stmt)
    ws_memberships = ws_res.scalars().all()

    ws_summaries = [
        MembershipSummary(
            id=m.id,
            target_id=m.workspace.id,
            name=m.workspace.name,
            slug=m.workspace.slug,
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
        )
        for m in ws_memberships
        if not m.workspace.is_deleted
    ]

    profile_dict = UserResponse.model_validate(current_user).model_dump()
    profile_dict["organizations"] = org_summaries
    profile_dict["workspaces"] = ws_summaries
    return UserProfileResponse(**profile_dict)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile information",
)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.first_name is not None:
        current_user.first_name = payload.first_name.strip()
    if payload.last_name is not None:
        current_user.last_name = payload.last_name.strip()
    if payload.display_name is not None:
        current_user.display_name = payload.display_name.strip()
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip()

    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Update account password and revoke other sessions",
)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password and confirmation do not match",
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must be at least 8 characters long",
        )

    current_user.password_hash = hash_password(payload.new_password)
    
    # Revoke all existing sessions for security
    revoke_stmt = (
        update(RefreshSession)
        .where(RefreshSession.user_id == current_user.id)
        .values(is_revoked=True)
    )
    await db.execute(revoke_stmt)
    await db.commit()

    return MessageResponse(message="Password successfully changed. Other active sessions revoked.")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset link",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(times=3, seconds=60, prefix="rl:forgot")),
):
    normalized_email = payload.email.lower().strip()
    stmt = select(User).where(User.email == normalized_email, User.is_deleted.is_(False))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    # Never expose whether email exists (Security best practice)
    if user:
        raw_token = generate_secure_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        reset_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False,
        )
        db.add(reset_record)
        await db.commit()

        # In dev mode, log reset link for easy local testing
        reset_url = f"http://localhost:3000/reset-password?token={raw_token}"
        logger.info("[DEV EMAIL] Password reset requested for %s. Reset URL: %s", user.email, reset_url)

    return MessageResponse(
        message="If an account exists with that email address, password reset instructions have been generated."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using a reset token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password and confirmation do not match",
        )

    token_hash = hash_token(payload.token)
    now = datetime.now(timezone.utc)

    stmt = (
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used.is_(False),
        )
        .options(selectinload(PasswordResetToken.user))
    )
    res = await db.execute(stmt)
    reset_entry = res.scalar_one_or_none()

    if not reset_entry or not reset_entry.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    token_expires = reset_entry.expires_at if reset_entry.expires_at.tzinfo else reset_entry.expires_at.replace(tzinfo=timezone.utc)
    if token_expires <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    # Update password
    user = reset_entry.user
    user.password_hash = hash_password(payload.new_password)
    reset_entry.is_used = True

    # Revoke sessions
    revoke_stmt = (
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id)
        .values(is_revoked=True)
    )
    await db.execute(revoke_stmt)
    await db.commit()

    return MessageResponse(message="Password has been successfully reset. Please log in with your new password.")

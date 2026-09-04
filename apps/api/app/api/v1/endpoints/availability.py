import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, verify_workspace_access
from app.models.scheduling import AvailabilityException, UserAvailability
from app.models.user import User
from app.schemas.scheduling import (
    AvailabilityExceptionCreate,
    AvailabilityExceptionResponse,
    UserAvailabilityCreate,
    UserAvailabilityResponse,
    UserAvailabilityUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=List[UserAvailabilityResponse],
    summary="List recurring availability for user in workspace",
)
async def list_availability(
    workspace_id: uuid.UUID = Query(..., description="Target workspace ID"),
    user_id: Optional[uuid.UUID] = Query(None, description="Specific user ID (defaults to self)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user, db)
    target_user_id = user_id or current_user.id

    stmt = (
        select(UserAvailability)
        .where(
            UserAvailability.workspace_id == workspace_id,
            UserAvailability.user_id == target_user_id,
            UserAvailability.is_active.is_(True),
        )
        .order_by(UserAvailability.day_of_week.asc(), UserAvailability.start_time.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "",
    response_model=UserAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recurring weekly availability block",
)
async def create_availability(
    payload: UserAvailabilityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(payload.workspace_id, current_user, db)
    target_user_id = payload.user_id or current_user.id

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be later than start_time",
        )

    avail = UserAvailability(
        user_id=target_user_id,
        workspace_id=payload.workspace_id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        timezone=payload.timezone,
        is_active=payload.is_active,
    )
    db.add(avail)
    await db.commit()
    await db.refresh(avail)
    return avail


@router.patch(
    "/{availability_id}",
    response_model=UserAvailabilityResponse,
    summary="Update recurring availability block",
)
async def update_availability(
    availability_id: uuid.UUID,
    payload: UserAvailabilityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserAvailability).where(UserAvailability.id == availability_id)
    avail = (await db.execute(stmt)).scalar_one_or_none()
    if not avail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability block not found")

    await verify_workspace_access(avail.workspace_id, current_user, db)

    if avail.user_id != current_user.id and current_user.role != "platform_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only edit own availability")

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(avail, field, val)

    if avail.end_time <= avail.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_time must be later than start_time")

    await db.commit()
    await db.refresh(avail)
    return avail


@router.delete(
    "/{availability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recurring availability block",
)
async def delete_availability(
    availability_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserAvailability).where(UserAvailability.id == availability_id)
    avail = (await db.execute(stmt)).scalar_one_or_none()
    if not avail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability block not found")

    await verify_workspace_access(avail.workspace_id, current_user, db)
    await db.delete(avail)
    await db.commit()


# --- AVAILABILITY EXCEPTIONS ---

@router.get(
    "/exceptions",
    response_model=List[AvailabilityExceptionResponse],
    summary="List availability exceptions (leave, holidays, blocked times)",
)
async def list_exceptions(
    workspace_id: uuid.UUID = Query(...),
    user_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, current_user, db)
    target_user_id = user_id or current_user.id

    stmt = (
        select(AvailabilityException)
        .where(
            AvailabilityException.workspace_id == workspace_id,
            AvailabilityException.user_id == target_user_id,
        )
        .order_by(AvailabilityException.start_at.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post(
    "/exceptions",
    response_model=AvailabilityExceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an availability exception",
)
async def create_exception(
    payload: AvailabilityExceptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(payload.workspace_id, current_user, db)
    target_user_id = payload.user_id or current_user.id

    if payload.end_at <= payload.start_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_at must be later than start_at")

    exc = AvailabilityException(
        user_id=target_user_id,
        workspace_id=payload.workspace_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        exception_type=payload.exception_type,
        reason=payload.reason,
    )
    db.add(exc)
    await db.commit()
    await db.refresh(exc)
    return exc

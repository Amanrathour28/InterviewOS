import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.scheduling import Notification
from app.models.user import User
from app.schemas.scheduling import NotificationResponse

router = APIRouter()


@router.get(
    "",
    response_model=List[NotificationResponse],
    summary="List in-app notifications for current user",
)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))

    res = await db.execute(query)
    notifications = res.scalars().all()

    return [
        NotificationResponse(
            id=n.id,
            workspace_id=n.workspace_id,
            user_id=n.user_id,
            notification_type=n.notification_type,
            title=n.title,
            message=n.message,
            extra_metadata=n.extra_metadata or {},
            read_at=n.read_at,
            created_at=n.created_at,
        )
        for n in notifications
    ]


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark single notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    notif = (await db.execute(stmt)).scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)

    return NotificationResponse(
        id=notif.id,
        workspace_id=notif.workspace_id,
        user_id=notif.user_id,
        notification_type=notif.notification_type,
        title=notif.title,
        message=notif.message,
        extra_metadata=notif.extra_metadata or {},
        read_at=notif.read_at,
        created_at=notif.created_at,
    )


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all unread notifications as read",
)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)
    await db.commit()

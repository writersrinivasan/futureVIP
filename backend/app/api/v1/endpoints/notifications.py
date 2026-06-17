"""Notification management endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, update

from app.api.v1.deps import CurrentUser, DBSession, Pagination
from app.core.logging import get_logger
from app.db.models import Notification
from app.db.schemas import MessageResponse, NotificationResponse, PaginatedResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])
logger = get_logger(__name__)


@router.get(
    "/",
    response_model=PaginatedResponse[NotificationResponse],
    summary="List notifications for the current user",
)
async def list_notifications(
    current_user: CurrentUser,
    db: DBSession,
    pagination: Pagination,
    unread_only: bool = False,
) -> PaginatedResponse[NotificationResponse]:
    """Return the current user's notifications, newest first."""
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read == False)  # noqa: E712

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(Notification.created_at.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    notifications = result.scalars().all()

    return PaginatedResponse.create(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> NotificationResponse:
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return NotificationResponse.model_validate(notification)


@router.put(
    "/read-all",
    response_model=MessageResponse,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Mark all unread notifications for the current user as read."""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    await db.commit()
    return MessageResponse(message="All notifications marked as read")


@router.delete(
    "/{notification_id}",
    response_model=MessageResponse,
    summary="Delete a notification",
)
async def delete_notification(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Delete a specific notification."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    await db.delete(notification)
    await db.commit()
    return MessageResponse(message="Notification deleted")

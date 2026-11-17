from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    UnreadNotificationCountResponse,
)


router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=list[NotificationResponse],
)
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Notification)
        .where(
            Notification.recipient_user_id
            == current_user.id
        )
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
    )

    if unread_only:
        query = query.where(
            Notification.is_read.is_(False)
        )

    return db.scalars(query).all()


@router.get(
    "/unread-count",
    response_model=UnreadNotificationCountResponse,
)
def unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.scalar(
        select(func.count(Notification.id))
        .where(
            Notification.recipient_user_id
            == current_user.id,
            Notification.is_read.is_(False),
        )
    )

    return {
        "unread_count": count or 0
    }


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = db.get(
        Notification,
        notification_id,
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    if (
        notification.recipient_user_id
        != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this notification"
            ),
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(
            timezone.utc
        )

        db.commit()
        db.refresh(notification)

    return notification


@router.patch(
    "/read-all",
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(
        timezone.utc
    )

    result = db.execute(
        update(Notification)
        .where(
            Notification.recipient_user_id
            == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(
            is_read=True,
            read_at=now,
        )
    )

    db.commit()

    return {
        "updated_count": result.rowcount or 0
    }
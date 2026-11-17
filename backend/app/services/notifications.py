from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User


def create_notification(
    db: Session,
    nonprofit_id: int,
    recipient_user_id: int,
    notification_type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification:
    notification = Notification(
        nonprofit_id=nonprofit_id,
        recipient_user_id=recipient_user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    db.add(notification)

    return notification


def notify_managers_and_admins(
    db: Session,
    nonprofit_id: int,
    notification_type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> None:
    users = db.scalars(
        select(User).where(
            User.nonprofit_id == nonprofit_id,
            User.role.in_(["manager", "admin"]),
            User.is_active.is_(True),
        )
    ).all()

    for user in users:
        create_notification(
            db=db,
            nonprofit_id=nonprofit_id,
            recipient_user_id=user.id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )


def notify_vendor_users(
    db: Session,
    nonprofit_id: int,
    vendor_id: int,
    notification_type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> None:
    users = db.scalars(
        select(User).where(
            User.nonprofit_id == nonprofit_id,
            User.vendor_id == vendor_id,
            User.role == "vendor",
            User.is_active.is_(True),
        )
    ).all()

    for user in users:
        create_notification(
            db=db,
            nonprofit_id=nonprofit_id,
            recipient_user_id=user.id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
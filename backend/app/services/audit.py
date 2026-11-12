from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def create_audit_log(
    db: Session,
    current_user: User,
    nonprofit_id: int,
    entity_type: str,
    entity_id: int,
    action: str,
    previous_status: str | None = None,
    new_status: str | None = None,
    description: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        nonprofit_id=nonprofit_id,
        performed_by_user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        description=description,
    )

    db.add(audit_log)

    return audit_log
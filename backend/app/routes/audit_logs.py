from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_roles
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse


router = APIRouter(
    prefix="/api/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    response_model=list[AuditLogResponse],
)
def list_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "staff",
            "manager",
            "admin",
        )
    ),
):
    query = (
        select(AuditLog)
        .where(
            AuditLog.nonprofit_id
            == current_user.nonprofit_id
        )
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
    )

    if entity_type is not None:
        query = query.where(
            AuditLog.entity_type
            == entity_type
        )

    if entity_id is not None:
        query = query.where(
            AuditLog.entity_id
            == entity_id
        )

    return db.scalars(query).all()
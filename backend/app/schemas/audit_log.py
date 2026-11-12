from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    nonprofit_id: int
    performed_by_user_id: int

    entity_type: str
    entity_id: int
    action: str

    previous_status: str | None
    new_status: str | None
    description: str | None

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
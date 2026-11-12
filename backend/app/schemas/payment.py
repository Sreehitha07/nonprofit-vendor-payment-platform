from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class PaymentFailureRequest(BaseModel):
    reason: str = Field(
        min_length=1,
        max_length=1000,
    )


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    created_by_user_id: int

    amount: Decimal
    currency: str

    status: str
    payment_method: str

    transaction_reference: str | None
    failure_reason: str | None

    scheduled_at: datetime
    processing_started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

class InvoiceStartReviewRequest(BaseModel):
    comments: str | None = Field(
        default=None,
        max_length=2000,
    )

class InvoiceDecisionRequest(BaseModel):
    decision: Literal[
        "approved",
        "rejected",
        "needs_documents",
    ]

    comments: str | None = Field(
        default=None,
        max_length=2000,
    )

    @model_validator(mode="after")
    def validate_comments(self):
        if (
            self.decision
            in {"rejected", "needs_documents"}
            and not self.comments
        ):
            raise ValueError(
                "Comments are required when rejecting "
                "an invoice or requesting documents"
            )

        return self


class InvoiceResubmitRequest(BaseModel):
    comments: str | None = Field(
        default=None,
        max_length=2000,
    )


class InvoiceReviewResponse(BaseModel):
    id: int
    invoice_id: int
    performed_by_user_id: int

    action: str
    previous_status: str
    new_status: str
    comments: str | None

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
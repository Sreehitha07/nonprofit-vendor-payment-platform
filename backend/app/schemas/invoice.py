from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InvoiceLineItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    category: str | None = None


class InvoiceLineItemResponse(BaseModel):
    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    category: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    nonprofit_id: int
    vendor_id: int

    invoice_number: str = Field(
        min_length=1,
        max_length=100,
    )

    invoice_date: date
    due_date: date | None = None

    currency: str = "USD"

    line_items: list[InvoiceLineItemCreate] = Field(
        min_length=1
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str):
        value = value.upper()

        if len(value) != 3 or not value.isalpha():
            raise ValueError(
                "Currency must be a 3-letter code such as USD"
            )

        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.due_date is not None
            and self.due_date < self.invoice_date
        ):
            raise ValueError(
                "Due date cannot be earlier than invoice date"
            )

        return self


class InvoiceResponse(BaseModel):
    id: int
    nonprofit_id: int
    vendor_id: int

    invoice_number: str
    invoice_date: date
    due_date: date | None

    total_amount: Decimal
    currency: str
    status: str

    created_at: datetime

    line_items: list[InvoiceLineItemResponse]

    model_config = ConfigDict(from_attributes=True)
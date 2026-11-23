from pydantic import BaseModel, ConfigDict


class ExtractedLineItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    description: str | None
    quantity: float | None
    unit_price: float | None
    line_total: float | None
    category: str | None


class ExtractedInvoice(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    vendor_name: str | None
    invoice_number: str | None
    invoice_date: str | None
    due_date: str | None
    currency: str | None
    total_amount: float | None

    line_items: list[ExtractedLineItem]

    document_type_guess: str | None

    extraction_method: str | None
    raw_text: str | None
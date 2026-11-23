from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AIAnalysisRequest(BaseModel):
    source_document_id: int | None = None


class AIInvoiceAnalysisResponse(BaseModel):
    id: int

    invoice_id: int

    source_document_id: int | None

    analyzed_by_user_id: int

    analysis_status: str

    completeness_score: float

    missing_fields: list[str]

    duplicate_risk: bool

    possible_duplicate_invoice_id: int | None

    risk_level: str

    risk_reasons: list[str]

    extracted_data: dict

    analysis_version: str

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
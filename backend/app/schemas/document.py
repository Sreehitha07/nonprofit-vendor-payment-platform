from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: int
    invoice_id: int
    uploaded_by_user_id: int

    original_filename: str
    document_type: str
    content_type: str
    file_size: int
    verification_status: str

    uploaded_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
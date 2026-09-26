from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class VendorBase(BaseModel):
    name: str
    contact_name: str | None = None
    email: EmailStr | None = None
    status: str = "pending"


class VendorCreate(VendorBase):
    nonprofit_id: int


class VendorUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    status: str | None = None


class VendorResponse(VendorBase):
    id: int
    nonprofit_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
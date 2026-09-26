from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class NonprofitBase(BaseModel):
    name: str
    registration_number: str | None = None
    email: EmailStr | None = None


class NonprofitCreate(NonprofitBase):
    pass


class NonprofitUpdate(BaseModel):
    name: str | None = None
    registration_number: str | None = None
    email: EmailStr | None = None


class NonprofitResponse(NonprofitBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
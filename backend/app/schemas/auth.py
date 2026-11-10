from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


UserRole = Literal[
    "vendor",
    "staff",
    "manager",
    "admin",
]


class UserRegister(BaseModel):
    nonprofit_id: int
    vendor_id: int | None = None

    full_name: str = Field(
        min_length=2,
        max_length=255,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: UserRole = "staff"

    @model_validator(mode="after")
    def validate_vendor_role(self):
        if self.role == "vendor" and self.vendor_id is None:
            raise ValueError(
                "vendor_id is required for vendor users"
            )

        if self.role != "vendor" and self.vendor_id is not None:
            raise ValueError(
                "vendor_id can only be assigned to vendor users"
            )

        return self


class UserResponse(BaseModel):
    id: int
    nonprofit_id: int
    vendor_id: int | None

    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
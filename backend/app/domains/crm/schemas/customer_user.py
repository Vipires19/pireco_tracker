from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.domains.crm.models import CustomerUserRole, CustomerUserStatus


class CustomerUserCreate(BaseModel):
    customer_id: int = Field(gt=0)
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)
    role: CustomerUserRole = CustomerUserRole.VIEWER
    status: CustomerUserStatus = CustomerUserStatus.ACTIVE
    must_change_password: bool = True

    @model_validator(mode="after")
    def passwords_must_match(self) -> "CustomerUserCreate":
        if self.password != self.password_confirm:
            raise ValueError("passwords_do_not_match")
        return self


class CustomerUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    role: CustomerUserRole | None = None
    must_change_password: bool | None = None


class CustomerUserStatusUpdate(BaseModel):
    status: CustomerUserStatus


class CustomerUserResetPassword(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)
    must_change_password: bool = True

    @model_validator(mode="after")
    def passwords_must_match(self) -> "CustomerUserResetPassword":
        if self.password != self.password_confirm:
            raise ValueError("passwords_do_not_match")
        return self


class CustomerUserResponse(BaseModel):
    id: int
    customer_id: int
    full_name: str
    email: EmailStr
    role: CustomerUserRole
    status: CustomerUserStatus
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerUserListResponse(BaseModel):
    items: list[CustomerUserResponse]
    total: int

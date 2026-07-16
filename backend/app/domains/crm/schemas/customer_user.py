from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.domains.crm.models import CustomerUserRole, CustomerUserStatus


class CustomerUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: CustomerUserRole = CustomerUserRole.VIEWER
    status: CustomerUserStatus = CustomerUserStatus.ACTIVE


class CustomerUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: CustomerUserRole | None = None
    status: CustomerUserStatus | None = None


class CustomerUserResponse(BaseModel):
    id: int
    customer_id: int
    full_name: str
    email: EmailStr
    role: CustomerUserRole
    status: CustomerUserStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerUserListResponse(BaseModel):
    items: list[CustomerUserResponse]
    total: int

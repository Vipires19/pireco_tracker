from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.domains.crm.models import CustomerStatus, DocumentType
from app.domains.crm.validators import (
    digits_only,
    validate_document,
    validate_phone,
    validate_state,
    validate_zip_code,
)


class CustomerBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    document: str = Field(min_length=11, max_length=18)
    document_type: DocumentType
    phone: str = Field(min_length=10, max_length=20)
    secondary_phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    zip_code: str | None = Field(default=None, max_length=9)
    street: str | None = Field(default=None, max_length=255)
    number: str | None = Field(default=None, max_length=20)
    complement: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_fields(self) -> "CustomerBase":
        self.document = validate_document(self.document, self.document_type)
        phone = validate_phone(self.phone, required=True)
        if phone is None:
            raise ValueError("invalid_phone")
        self.phone = phone
        self.secondary_phone = validate_phone(self.secondary_phone or "", required=False)
        self.zip_code = validate_zip_code(self.zip_code)
        self.state = validate_state(self.state)
        return self


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(CustomerBase):
    pass


class CustomerStatusUpdate(BaseModel):
    status: CustomerStatus


class CustomerResponse(BaseModel):
    id: int
    company_id: int | None
    full_name: str
    document: str
    document_type: DocumentType
    phone: str
    secondary_phone: str | None
    email: str | None
    zip_code: str | None
    street: str | None
    number: str | None
    complement: str | None
    district: str | None
    city: str | None
    state: str | None
    notes: str | None
    status: CustomerStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerStats(BaseModel):
    total: int
    active: int
    inactive: int


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int
    pages: int
    stats: CustomerStats


class CustomerSortField(StrEnum):
    FULL_NAME = "full_name"
    CREATED_AT = "created_at"
    CITY = "city"
    STATUS = "status"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"

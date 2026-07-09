from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.domains.fleet.models import VehicleCategory, VehicleFuel, VehicleStatus
from app.domains.fleet.validators import (
    normalize_plate,
    validate_category,
    validate_chassis,
    validate_cover_image,
    validate_fuel,
    validate_odometer,
    validate_renavam,
    validate_year,
)


class VehicleBase(BaseModel):
    customer_id: int = Field(gt=0)
    plate: str = Field(min_length=7, max_length=10)
    nickname: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    version: str | None = Field(default=None, max_length=100)
    year_model: int | None = Field(default=None, ge=1900)
    year_manufacture: int | None = Field(default=None, ge=1900)
    color: str | None = Field(default=None, max_length=50)
    fuel: VehicleFuel | None = None
    renavam: str | None = Field(default=None, max_length=14)
    chassis: str | None = Field(default=None, max_length=20)
    category: VehicleCategory | None = None
    cover_image: HttpUrl | str | None = None
    odometer: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_fields(self) -> "VehicleBase":
        self.plate = normalize_plate(self.plate)
        self.renavam = validate_renavam(self.renavam)
        self.chassis = validate_chassis(self.chassis)
        self.year_model = validate_year(self.year_model, field_name="year_model")
        self.year_manufacture = validate_year(self.year_manufacture, field_name="year_manufacture")
        self.odometer = validate_odometer(self.odometer)
        self.category = validate_category(self.category)
        self.fuel = validate_fuel(self.fuel)
        if self.cover_image is not None:
            self.cover_image = validate_cover_image(str(self.cover_image))
        if self.nickname is not None:
            self.nickname = self.nickname.strip() or None
        return self


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(VehicleBase):
    pass


class VehicleStatusUpdate(BaseModel):
    status: VehicleStatus


class VehicleResponse(BaseModel):
    id: int
    customer_id: int
    plate: str
    nickname: str | None
    brand: str | None
    model: str | None
    version: str | None
    year_model: int | None
    year_manufacture: int | None
    color: str | None
    fuel: VehicleFuel | None
    renavam: str | None
    chassis: str | None
    category: VehicleCategory | None
    cover_image: str | None
    odometer: int | None
    notes: str | None
    status: VehicleStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VehicleStats(BaseModel):
    total: int
    active: int
    inactive: int
    pending_installation: int
    in_stock: int


class VehicleListResponse(BaseModel):
    items: list[VehicleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    stats: VehicleStats


class VehicleSortField(StrEnum):
    PLATE = "plate"
    NICKNAME = "nickname"
    BRAND = "brand"
    MODEL = "model"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"

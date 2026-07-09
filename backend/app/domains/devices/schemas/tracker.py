from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.domains.devices.models import HealthStatus, TrackerOrigin, TrackerStatus
from app.domains.devices.validators import (
    validate_firmware,
    validate_iccid,
    validate_imei,
    validate_manufacturer,
    validate_model,
    validate_serial_number,
    validate_sim_imei,
    validate_tracker_phone,
)


class TrackerBase(BaseModel):
    imei: str = Field(min_length=15, max_length=20)
    model: str | None = Field(default=None, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=100)
    firmware: str | None = Field(default=None, max_length=100)
    tracker_phone_number: str | None = Field(default=None, max_length=20)
    sim_iccid: str | None = Field(default=None, max_length=24)
    sim_imei: str | None = Field(default=None, max_length=20)
    carrier: str | None = Field(default=None, max_length=100)
    apn: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    origin: TrackerOrigin = Field(default=TrackerOrigin.MANUAL)

    @model_validator(mode="after")
    def validate_fields(self) -> "TrackerBase":
        self.imei = validate_imei(self.imei)
        self.model = validate_model(self.model)
        self.manufacturer = validate_manufacturer(self.manufacturer)
        self.firmware = validate_firmware(self.firmware)
        self.tracker_phone_number = validate_tracker_phone(self.tracker_phone_number)
        self.sim_iccid = validate_iccid(self.sim_iccid)
        self.sim_imei = validate_sim_imei(self.sim_imei)
        self.serial_number = validate_serial_number(self.serial_number)
        if self.carrier is not None:
            self.carrier = self.carrier.strip() or None
        if self.apn is not None:
            self.apn = self.apn.strip() or None
        if self.notes is not None:
            self.notes = self.notes.strip() or None
        return self


class TrackerCreate(TrackerBase):
    status: TrackerStatus | None = Field(default=None)


class TrackerUpdate(TrackerBase):
    pass


class TrackerStatusUpdate(BaseModel):
    status: TrackerStatus


class TrackerResponse(BaseModel):
    id: int
    imei: str
    model: str | None
    manufacturer: str | None
    firmware: str | None
    tracker_phone_number: str | None
    sim_iccid: str | None
    sim_imei: str | None
    carrier: str | None
    apn: str | None
    serial_number: str | None
    notes: str | None
    status: TrackerStatus
    health_status: HealthStatus
    origin: TrackerOrigin
    last_seen_at: datetime | None
    last_ip: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrackerAssignmentCreate(BaseModel):
    tracker_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)


class TrackerAssignmentUnassign(BaseModel):
    removal_reason: str | None = Field(default=None, max_length=500)


class TrackerAssignmentResponse(BaseModel):
    id: int
    tracker_id: int
    vehicle_id: int
    installed_at: datetime
    removed_at: datetime | None
    installed_by: int | None
    removed_by: int | None
    removal_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrackerStats(BaseModel):
    total: int
    in_stock: int
    installed: int
    maintenance: int
    blocked: int


class TrackerListResponse(BaseModel):
    items: list[TrackerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    stats: TrackerStats


class TrackerSortField(StrEnum):
    IMEI = "imei"
    MODEL = "model"
    STATUS = "status"
    CREATED_AT = "created_at"
    LAST_SEEN_AT = "last_seen_at"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"

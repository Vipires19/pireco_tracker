from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domains.devices.models import InstallationStatus, InstallationType


class InstallationChecklist(BaseModel):
    power_connected: bool = False
    gps_ok: bool = False
    gsm_ok: bool = False
    ignition_ok: bool = False
    blocking_ok: bool = False
    test_drive_completed: bool = False
    customer_present: bool = False


class InstallationCreate(BaseModel):
    tracker_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)
    installation_type: InstallationType = InstallationType.PRIMARY
    installed_by: int | None = Field(default=None, gt=0)
    installation_notes: str | None = Field(default=None, max_length=2000)
    checklist: InstallationChecklist = Field(default_factory=InstallationChecklist)
    complete: bool = False


class InstallationUpdate(BaseModel):
    installation_type: InstallationType | None = None
    installed_by: int | None = Field(default=None, gt=0)
    installation_notes: str | None = Field(default=None, max_length=2000)
    checklist: InstallationChecklist | None = None
    status: InstallationStatus | None = None
    removal_reason: str | None = Field(default=None, max_length=500)


class InstallationFinish(BaseModel):
    installation_notes: str | None = Field(default=None, max_length=2000)


class TrackerSummary(BaseModel):
    id: int
    imei: str
    model: str | None
    last_seen_at: datetime | None

    model_config = {"from_attributes": True}


class VehicleSummary(BaseModel):
    id: int
    plate: str
    nickname: str | None

    model_config = {"from_attributes": True}


class CustomerSummary(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


class TechnicianSummary(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


class InstallationResponse(BaseModel):
    id: int
    tracker_id: int
    vehicle_id: int
    installation_type: InstallationType
    status: InstallationStatus
    installed_at: datetime
    installed_by: int | None
    installation_notes: str | None
    power_connected: bool
    gps_ok: bool
    gsm_ok: bool
    ignition_ok: bool
    blocking_ok: bool
    test_drive_completed: bool
    customer_present: bool
    removed_at: datetime | None
    removed_by: int | None
    removal_reason: str | None
    created_at: datetime
    updated_at: datetime
    tracker: TrackerSummary
    vehicle: VehicleSummary
    customer: CustomerSummary
    technician: TechnicianSummary | None

    model_config = {"from_attributes": True}


class InstallationListResponse(BaseModel):
    items: list[InstallationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class InstallationSortField(StrEnum):
    INSTALLED_AT = "installed_at"
    CREATED_AT = "created_at"
    STATUS = "status"
    INSTALLATION_TYPE = "installation_type"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"

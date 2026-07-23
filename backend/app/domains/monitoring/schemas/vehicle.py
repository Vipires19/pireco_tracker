from datetime import datetime

from pydantic import BaseModel, Field

from app.domains.devices.models import HealthStatus


class MonitoringVehicleItem(BaseModel):
    vehicle_id: int
    plate: str
    model: str | None
    customer_name: str
    tracker_id: int
    tracker_imei: str
    health: HealthStatus
    latitude: float | None
    longitude: float | None
    speed: float | None
    course: int | None
    last_seen_at: datetime | None
    gps_time: datetime | None


class MonitoringCustomerInfo(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


class MonitoringVehicleInfo(BaseModel):
    id: int
    plate: str
    model: str | None
    brand: str | None
    nickname: str | None

    model_config = {"from_attributes": True}


class MonitoringTrackerInfo(BaseModel):
    id: int
    imei: str
    model: str | None
    last_seen_at: datetime | None
    last_latitude: float | None
    last_longitude: float | None
    last_speed: float | None
    last_course: int | None
    last_gps_time: datetime | None

    model_config = {"from_attributes": True}


class MonitoringVehicleDetail(BaseModel):
    customer: MonitoringCustomerInfo
    vehicle: MonitoringVehicleInfo
    tracker: MonitoringTrackerInfo
    health: HealthStatus
    last_seen_at: datetime | None = Field(description="Última comunicação do rastreador")
    latitude: float | None = Field(default=None, description="Última latitude conhecida")
    longitude: float | None = Field(default=None, description="Última longitude conhecida")
    speed: float | None = None
    course: int | None = None
    gps_time: datetime | None = None

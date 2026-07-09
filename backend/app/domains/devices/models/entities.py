from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domains.fleet.models import Vehicle
    from app.models.entities import DeviceEvent, Position


class TrackerStatus(StrEnum):
    NEW = "NEW"
    IN_STOCK = "IN_STOCK"
    PENDING_INSTALLATION = "PENDING_INSTALLATION"
    INSTALLED = "INSTALLED"
    MAINTENANCE = "MAINTENANCE"
    BLOCKED = "BLOCKED"
    LOST = "LOST"
    DAMAGED = "DAMAGED"
    DISPOSED = "DISPOSED"


class HealthStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TrackerOrigin(StrEnum):
    MANUAL = "MANUAL"
    AUTO_DISCOVERY = "AUTO_DISCOVERY"
    IMPORT = "IMPORT"


class InstallationType(StrEnum):
    PRIMARY = "PRIMARY"
    BAIT = "BAIT"
    AUXILIARY = "AUXILIARY"


class InstallationStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    INSTALLED = "INSTALLED"
    REMOVED = "REMOVED"
    CANCELLED = "CANCELLED"


class TrackerAuditAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    DELETED = "deleted"


class Tracker(Base):
    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    imei: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    firmware: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracker_phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    sim_iccid: Mapped[str | None] = mapped_column(String(22), nullable=True, index=True)
    sim_imei: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    carrier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    apn: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=TrackerStatus.IN_STOCK, index=True
    )
    health_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=HealthStatus.UNKNOWN, index=True
    )
    origin: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TrackerOrigin.MANUAL, index=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignments: Mapped[list["TrackerAssignment"]] = relationship(
        back_populates="tracker", order_by="TrackerAssignment.installed_at.desc()"
    )
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="tracker")
    events: Mapped[list["DeviceEvent"]] = relationship("DeviceEvent", back_populates="tracker")


class TrackerAssignment(Base):
    __tablename__ = "tracker_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracker_id: Mapped[int] = mapped_column(
        ForeignKey("trackers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    installed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    removed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    removal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    installation_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InstallationType.PRIMARY, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InstallationStatus.PENDING, index=True
    )
    installation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    power_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gps_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gsm_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ignition_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocking_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    test_drive_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    customer_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tracker: Mapped["Tracker"] = relationship(back_populates="assignments")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="tracker_assignments")


class TrackerAuditLog(Base):
    __tablename__ = "tracker_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracker_id: Mapped[int | None] = mapped_column(
        ForeignKey("trackers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

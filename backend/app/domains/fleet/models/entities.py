from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domains.crm.models import Customer
    from app.domains.devices.models import TrackerAssignment


class VehicleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING_INSTALLATION = "PENDING_INSTALLATION"
    IN_STOCK = "IN_STOCK"
    DECOMMISSIONED = "DECOMMISSIONED"


class VehicleCategory(StrEnum):
    CAR = "CAR"
    MOTORCYCLE = "MOTORCYCLE"
    TRUCK = "TRUCK"
    TRAILER = "TRAILER"
    IMPLEMENT = "IMPLEMENT"
    OTHER = "OTHER"


class VehicleFuel(StrEnum):
    GASOLINE = "GASOLINE"
    ETHANOL = "ETHANOL"
    FLEX = "FLEX"
    DIESEL = "DIESEL"
    ELECTRIC = "ELECTRIC"
    HYBRID = "HYBRID"
    GNV = "GNV"
    OTHER = "OTHER"


class VehicleAuditAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    DELETED = "deleted"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plate: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_model: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_manufacture: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fuel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    renavam: Mapped[str | None] = mapped_column(String(11), nullable=True, index=True)
    chassis: Mapped[str | None] = mapped_column(String(17), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    cover_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    odometer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VehicleStatus.ACTIVE, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="vehicles")
    tracker_assignments: Mapped[list["TrackerAssignment"]] = relationship(
        "TrackerAssignment", back_populates="vehicle"
    )


class VehicleAuditLog(Base):
    __tablename__ = "vehicle_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True
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

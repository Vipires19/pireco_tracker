"""Entidades de telemetria e cadastro multi-tenant."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    fleets: Mapped[list["Fleet"]] = relationship(back_populates="company")
    trackers: Mapped[list["Tracker"]] = relationship(back_populates="company")


class Fleet(Base):
    __tablename__ = "fleets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="fleets")


class Vehicle(Base):
    """Stub mínimo — schema completo no domínio Fleet do backend."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    tracker_assignments: Mapped[list["TrackerAssignment"]] = relationship(
        back_populates="vehicle"
    )


class Tracker(Base):
    """Cadastro ERP de rastreadores — sync de telemetria (last_seen / health / GPS)."""

    __tablename__ = "trackers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Coluna legada multi-tenant (server_default=1); não usada pela lógica ERP.
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    imei: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    model: Mapped[str | None] = mapped_column(String(100))
    manufacturer: Mapped[str | None] = mapped_column(String(100))
    firmware: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    health_status: Mapped[str] = mapped_column(String(20), default="UNKNOWN", nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_ip: Mapped[str | None] = mapped_column(String(45))
    last_remote_ip: Mapped[str | None] = mapped_column(String(45))
    protocol: Mapped[str | None] = mapped_column(String(50))
    last_latitude: Mapped[float | None] = mapped_column(Float)
    last_longitude: Mapped[float | None] = mapped_column(Float)
    last_speed: Mapped[float | None] = mapped_column(Float)
    last_course: Mapped[int | None] = mapped_column(Integer)
    last_gps_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="trackers")
    assignments: Mapped[list["TrackerAssignment"]] = relationship(back_populates="tracker")
    positions: Mapped[list["Position"]] = relationship(back_populates="tracker")
    events: Mapped[list["DeviceEvent"]] = relationship(back_populates="tracker")


class TrackerAssignment(Base):
    __tablename__ = "tracker_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracker_id: Mapped[int] = mapped_column(ForeignKey("trackers.id"), index=True, nullable=False)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(default=True, nullable=False)

    tracker: Mapped["Tracker"] = relationship(back_populates="assignments")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="tracker_assignments")


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        Index("ix_positions_imei_received_at", "tracker_imei", "received_at"),
        Index("ix_positions_tracker_id_received_at", "tracker_id", "received_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracker_id: Mapped[int] = mapped_column(ForeignKey("trackers.id"), index=True, nullable=False)
    tracker_imei: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(36), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    speed_kmh: Mapped[float | None] = mapped_column(Float)
    course_degrees: Mapped[int | None] = mapped_column(Integer)
    gps_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    connection_id: Mapped[str] = mapped_column(String(36), nullable=False)
    remote_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tracker: Mapped["Tracker"] = relationship(back_populates="positions")


class DeviceEvent(Base):
    __tablename__ = "device_events"
    __table_args__ = (
        Index("ix_device_events_imei_received_at", "tracker_imei", "received_at"),
        Index("ix_device_events_category", "event_category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracker_id: Mapped[int] = mapped_column(ForeignKey("trackers.id"), index=True, nullable=False)
    tracker_imei: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(36), index=True)
    event_code: Mapped[str] = mapped_column(String(50), nullable=False)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    connection_id: Mapped[str] = mapped_column(String(36), nullable=False)
    remote_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tracker: Mapped["Tracker"] = relationship(back_populates="events")


class ProcessedEvent(Base):
    """Registro de idempotência — evita processamento duplicado."""

    __tablename__ = "processed_events"
    __table_args__ = (Index("ix_processed_events_imei", "tracker_imei"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tracker_imei: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

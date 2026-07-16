"""Contratos versionados compartilhados entre serviços."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

SCHEMA_VERSION = 1


class MessageType(StrEnum):
    POSITION = "position"
    HEARTBEAT = "heartbeat"
    EVENT = "event"
    CONNECTION = "connection"


@dataclass(frozen=True)
class BaseContract:
    schema_version: int
    trace_id: str
    tracker_imei: str
    received_at: datetime
    connection_id: str
    remote_ip: str
    source_protocol: str = "unknown"
    serial_number: int | None = None
    payload_hash: str | None = None

    @property
    def message_type(self) -> MessageType:
        raise NotImplementedError

    def dedup_key(self) -> str:
        if self.message_type == MessageType.HEARTBEAT:
            parts = [
                self.tracker_imei,
                "heartbeat",
                str(self.serial_number or ""),
                self.received_at.isoformat(),
            ]
        elif self.message_type == MessageType.CONNECTION:
            parts = [
                self.tracker_imei,
                "connection",
                self.action,
                self.connection_id,
                self.received_at.isoformat(),
            ]
        else:
            parts = [
                self.tracker_imei,
                self.message_type.value,
                str(self.serial_number or ""),
                self.payload_hash or "",
            ]
            if isinstance(self, DevicePosition) and self.gps_time:
                parts.append(self.gps_time.isoformat())
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def to_stream_fields(self) -> dict[str, str]:
        return serialize_contract(self)


@dataclass(frozen=True)
class DevicePosition(BaseContract):
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    course_degrees: int | None = None
    gps_time: datetime | None = None

    @property
    def message_type(self) -> MessageType:
        return MessageType.POSITION


@dataclass(frozen=True)
class DeviceHeartbeat(BaseContract):
    terminal_info: str | None = None
    voltage_level: str | None = None
    gsm_signal: int | None = None

    @property
    def message_type(self) -> MessageType:
        return MessageType.HEARTBEAT


@dataclass(frozen=True)
class DeviceEvent(BaseContract):
    event_code: str = ""
    event_category: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def message_type(self) -> MessageType:
        return MessageType.EVENT


@dataclass(frozen=True)
class DeviceConnection(BaseContract):
    action: str = ""
    manufacturer: str | None = None
    model: str | None = None
    firmware: str | None = None

    @property
    def message_type(self) -> MessageType:
        return MessageType.CONNECTION


@dataclass(frozen=True)
class CommandResult:
    schema_version: int
    trace_id: str
    tracker_imei: str
    command_type: str
    success: bool
    message: str
    received_at: datetime

    def to_stream_fields(self) -> dict[str, str]:
        return {
            "schema_version": str(self.schema_version),
            "trace_id": self.trace_id,
            "tracker_imei": self.tracker_imei,
            "command_type": self.command_type,
            "success": str(self.success).lower(),
            "message": self.message,
            "received_at": self.received_at.isoformat(),
            "message_type": "command_result",
        }


DomainMessage = DevicePosition | DeviceHeartbeat | DeviceEvent | DeviceConnection


def compute_payload_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def serialize_contract(message: DomainMessage | CommandResult) -> dict[str, str]:
    if isinstance(message, CommandResult):
        return message.to_stream_fields()

    payload = asdict(message)
    result: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = json.dumps(value)
        elif value is None:
            result[key] = ""
        else:
            result[key] = str(value)
    result["message_type"] = message.message_type.value
    if "schema_version" not in result or not result["schema_version"]:
        result["schema_version"] = str(SCHEMA_VERSION)
    return result


def parse_stream_fields(fields: dict[str, str]) -> DomainMessage | None:
    message_type = fields.get("message_type")
    if not message_type or not fields.get("tracker_imei"):
        return None

    common = {
        "schema_version": int(fields.get("schema_version", SCHEMA_VERSION)),
        "trace_id": fields.get("trace_id", ""),
        "tracker_imei": fields["tracker_imei"],
        "connection_id": fields.get("connection_id", ""),
        "remote_ip": fields.get("remote_ip", ""),
        "received_at": _parse_dt(fields.get("received_at")),
        "source_protocol": fields.get("source_protocol", "unknown"),
        "serial_number": _parse_int(fields.get("serial_number")),
        "payload_hash": fields.get("payload_hash") or None,
    }

    if message_type == MessageType.POSITION:
        return DevicePosition(
            **common,
            latitude=_parse_float(fields.get("latitude")),
            longitude=_parse_float(fields.get("longitude")),
            speed_kmh=_parse_float(fields.get("speed_kmh")),
            course_degrees=_parse_int(fields.get("course_degrees")),
            gps_time=_parse_dt(fields.get("gps_time")),
        )
    if message_type == MessageType.HEARTBEAT:
        return DeviceHeartbeat(
            **common,
            terminal_info=fields.get("terminal_info") or None,
            voltage_level=fields.get("voltage_level") or None,
            gsm_signal=_parse_int(fields.get("gsm_signal")),
        )
    if message_type == MessageType.EVENT:
        meta_raw = fields.get("metadata", "")
        metadata = json.loads(meta_raw) if meta_raw else {}
        return DeviceEvent(
            **common,
            event_code=fields.get("event_code", "unknown"),
            event_category=fields.get("event_category", "unknown"),
            metadata=metadata,
        )
    if message_type == MessageType.CONNECTION:
        return DeviceConnection(
            **common,
            action=fields.get("action", "unknown"),
            manufacturer=fields.get("manufacturer") or None,
            model=fields.get("model") or None,
            firmware=fields.get("firmware") or None,
        )
    return None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value)


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)

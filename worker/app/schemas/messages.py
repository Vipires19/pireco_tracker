"""Contratos protocolo-agnósticos consumidos do Redis Streams."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(StrEnum):
    POSITION = "position"
    HEARTBEAT = "heartbeat"
    EVENT = "event"
    CONNECTION = "connection"


class StreamMessage(BaseModel):
    message_type: MessageType
    tracker_imei: str
    connection_id: str
    remote_ip: str
    received_at: datetime
    published_at: datetime | None = None
    source_protocol: str = Field(default="unknown")


class PositionMessage(StreamMessage):
    message_type: MessageType = MessageType.POSITION
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    course_degrees: int | None = None
    gps_time: datetime | None = None


class HeartbeatMessage(StreamMessage):
    message_type: MessageType = MessageType.HEARTBEAT
    terminal_info: str | None = None
    voltage_level: str | None = None
    gsm_signal: int | None = None


class EventMessage(StreamMessage):
    message_type: MessageType = MessageType.EVENT
    event_code: str
    event_category: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectionMessage(StreamMessage):
    message_type: MessageType = MessageType.CONNECTION
    action: str

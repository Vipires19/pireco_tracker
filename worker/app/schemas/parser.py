"""Parser de mensagens do Redis Stream — sem conhecimento de protocolo."""

import json
from datetime import datetime

from app.schemas.messages import (
    ConnectionMessage,
    EventMessage,
    HeartbeatMessage,
    MessageType,
    PositionMessage,
    StreamMessage,
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def parse_stream_fields(fields: dict[str, str]) -> StreamMessage | None:
    message_type = fields.get("message_type")
    if not message_type:
        return None

    common = {
        "tracker_imei": fields.get("tracker_imei", ""),
        "connection_id": fields.get("connection_id", ""),
        "remote_ip": fields.get("remote_ip", ""),
        "received_at": _parse_datetime(fields.get("received_at")) or datetime.now(),
        "published_at": _parse_datetime(fields.get("published_at")),
        "source_protocol": fields.get("source_protocol", "unknown"),
    }

    if not common["tracker_imei"]:
        return None

    if message_type == MessageType.POSITION:
        return PositionMessage(
            **common,
            latitude=_float_or_none(fields.get("latitude")),
            longitude=_float_or_none(fields.get("longitude")),
            speed_kmh=_float_or_none(fields.get("speed_kmh")),
            course_degrees=_int_or_none(fields.get("course_degrees")),
            gps_time=_parse_datetime(fields.get("gps_time")),
        )

    if message_type == MessageType.HEARTBEAT:
        return HeartbeatMessage(
            **common,
            terminal_info=fields.get("terminal_info") or None,
            voltage_level=fields.get("voltage_level") or None,
            gsm_signal=_int_or_none(fields.get("gsm_signal")),
        )

    if message_type == MessageType.EVENT:
        metadata_raw = fields.get("metadata", "")
        metadata = json.loads(metadata_raw) if metadata_raw else {}
        return EventMessage(
            **common,
            event_code=fields.get("event_code", "unknown"),
            event_category=fields.get("event_category", "unknown"),
            metadata=metadata,
        )

    if message_type == MessageType.CONNECTION:
        return ConnectionMessage(
            **common,
            action=fields.get("action", "unknown"),
        )

    return None


def _float_or_none(value: str | None) -> float | None:
    if not value:
        return None
    return float(value)


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)

"""Utilitários de decodificação de payload GT06."""

from __future__ import annotations

from datetime import UTC, datetime

from app.protocols.gt06.packets import PacketType, ProtocolNumber, packet_type_for


def bcd_to_imei(bcd_bytes: bytes) -> str:
    digits: list[str] = []
    for byte in bcd_bytes:
        digits.append(str((byte >> 4) & 0x0F))
        digits.append(str(byte & 0x0F))
    return "".join(digits).lstrip("0")


def imei_to_bcd(imei: str) -> bytes:
    digits = imei.zfill(16)
    return bytes((int(digits[i]) << 4) | int(digits[i + 1]) for i in range(0, 16, 2))


def decode_login_imei(payload: bytes) -> str | None:
    if len(payload) < 8:
        return None
    return bcd_to_imei(payload[:8])


def decode_gps_datetime(payload: bytes, offset: int = 0) -> datetime | None:
    if len(payload) < offset + 6:
        return None
    year = 2000 + payload[offset]
    month = payload[offset + 1]
    day = payload[offset + 2]
    hour = payload[offset + 3]
    minute = payload[offset + 4]
    second = payload[offset + 5]
    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except ValueError:
        return None


def decode_gps_coordinates(payload: bytes) -> tuple[float | None, float | None]:
    if len(payload) < 18:
        return None, None

    lat_raw = int.from_bytes(payload[8:12], "big")
    lon_raw = int.from_bytes(payload[12:16], "big")

    latitude = lat_raw / 1_800_000.0
    longitude = lon_raw / 1_800_000.0

    course_status = int.from_bytes(payload[16:18], "big")
    if course_status & 0x0400:
        latitude = -latitude
    if course_status & 0x0800:
        longitude = -longitude

    return latitude, longitude


def decode_gps_speed(payload: bytes) -> float | None:
    if len(payload) < 19:
        return None
    return float(payload[18])


def decode_gps_course(payload: bytes) -> int | None:
    if len(payload) < 18:
        return None
    course_status = int.from_bytes(payload[16:18], "big")
    return course_status & 0x03FF


def packet_category(protocol_number: int) -> str:
    mapping = {
        PacketType.LOGIN: "login",
        PacketType.GPS: "position",
        PacketType.HEARTBEAT: "heartbeat",
        PacketType.ALARM: "event",
        PacketType.STATUS: "status",
        PacketType.LBS: "lbs",
        PacketType.COMMAND_RESPONSE: "command_response",
    }
    return mapping.get(packet_type_for(protocol_number), "unknown")

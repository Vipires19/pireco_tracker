"""Utilitários de decodificação de payload GT06."""

from __future__ import annotations

from datetime import UTC, datetime

from app.protocols.gt06.packets import PacketType, packet_type_for

# Fórmula oficial GT06: minutos decimais * 30000 == graus * 1_800_000
_GPS_SCALE = 1_800_000.0
_COURSE_NORTH = 0x0400  # BYTE_1 bit2 — 1 = Norte, 0 = Sul
_COURSE_WEST = 0x0800  # BYTE_1 bit3 — 1 = Oeste, 0 = Leste
_COURSE_MASK = 0x03FF


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


def decode_login_firmware(payload: bytes) -> str | None:
    """Extrai firmware/versão do login apenas se o pacote trouxer bytes explícitos."""
    # Layout clássico GT06 login = 8 bytes IMEI (BCD). Bytes extras são raros/variante.
    if len(payload) < 10:
        return None
    # Alguns firmwares anexam ASCII após o IMEI; só aceitar se for imprimível.
    extra = payload[8:]
    text = "".join(chr(b) for b in extra if 32 <= b < 127).strip()
    return text or None


def decode_gps_datetime(payload: bytes, offset: int = 0) -> datetime | None:
    """DateTime GT06: 6 bytes binários (não BCD) em UTC — YY MM DD hh mm ss."""
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


def decode_gps_satellites(payload: bytes) -> int | None:
    if len(payload) < 7:
        return None
    return payload[6] & 0x0F


def decode_gps_coordinates(payload: bytes) -> tuple[float | None, float | None]:
    """
    Layout oficial (0x12 / 0x22):

    [0:6]  DateTime
    [6]    Length/satellites (1 byte)
    [7:11] Latitude uint32 BE
    [11:15] Longitude uint32 BE
    [15]   Speed
    [16:18] Course/Status

    graus = raw / 1_800_000  (== raw / 30000 / 60)
    """
    if len(payload) < 18:
        return None, None

    lat_raw = int.from_bytes(payload[7:11], "big")
    lon_raw = int.from_bytes(payload[11:15], "big")

    latitude = lat_raw / _GPS_SCALE
    longitude = lon_raw / _GPS_SCALE

    course_status = int.from_bytes(payload[16:18], "big")
    # Spec / Traccar: bit10=0 → Sul; bit11=1 → Oeste
    if not (course_status & _COURSE_NORTH):
        latitude = -latitude
    if course_status & _COURSE_WEST:
        longitude = -longitude

    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        return None, None

    return latitude, longitude


def decode_gps_speed(payload: bytes) -> float | None:
    """Velocidade em km/h (1 byte, 0–255)."""
    if len(payload) < 16:
        return None
    return float(payload[15])


def decode_gps_course(payload: bytes) -> int | None:
    if len(payload) < 18:
        return None
    course_status = int.from_bytes(payload[16:18], "big")
    return course_status & _COURSE_MASK


def encode_gps_course_status(course: int, *, latitude: float, longitude: float) -> int:
    status = course & _COURSE_MASK
    if latitude >= 0:
        status |= _COURSE_NORTH
    if longitude < 0:
        status |= _COURSE_WEST
    status |= 0x1000  # GPS positioned
    return status


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

"""Codificação de respostas e pacotes GT06."""

from datetime import UTC, datetime

from app.protocol.constants import START_BYTES_SHORT, STOP_BYTES, ProtocolNumber
from app.protocol.crc import crc16_x25
from app.protocol.packets import imei_to_bcd


def build_ack(protocol_number: int, serial_number: int) -> bytes:
    body = bytes([0x05, protocol_number]) + serial_number.to_bytes(2, "big")
    crc = crc16_x25(body)
    return START_BYTES_SHORT + body + crc.to_bytes(2, "big") + STOP_BYTES


def _build_short_packet(protocol: int, payload: bytes, serial_number: int) -> bytes:
    serial_bytes = serial_number.to_bytes(2, "big")
    content = bytes([protocol]) + payload + serial_bytes
    length = len(content) + 2
    crc_data = bytes([length]) + content
    crc = crc16_x25(crc_data)
    return START_BYTES_SHORT + crc_data + crc.to_bytes(2, "big") + STOP_BYTES


def build_login_packet(imei: str, serial_number: int = 1) -> bytes:
    return _build_short_packet(ProtocolNumber.LOGIN, imei_to_bcd(imei), serial_number)


def build_heartbeat_packet(
    serial_number: int = 2,
    terminal_info: int = 0x00,
    voltage: int = 0x06,
    gsm_signal: int = 0x04,
) -> bytes:
    payload = bytes([terminal_info, voltage, gsm_signal])
    return _build_short_packet(ProtocolNumber.HEARTBEAT, payload, serial_number)


def build_gps_packet(
    latitude: float,
    longitude: float,
    speed_kmh: float = 0.0,
    course: int = 0,
    gps_time: datetime | None = None,
    serial_number: int = 3,
    satellites: int = 8,
) -> bytes:
    now = gps_time or datetime.now(UTC)
    datetime_bytes = bytes(
        [
            now.year % 100,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
        ]
    )

    lat_raw = int(abs(latitude) * 1_800_000)
    lon_raw = int(abs(longitude) * 1_800_000)

    course_status = course & 0x03FF
    if latitude < 0:
        course_status |= 0x0400
    if longitude < 0:
        course_status |= 0x0800

    payload = (
        datetime_bytes
        + bytes([0x0C, satellites])
        + lat_raw.to_bytes(4, "big")
        + lon_raw.to_bytes(4, "big")
        + bytes([int(speed_kmh)])
        + course_status.to_bytes(2, "big")
    )
    return _build_short_packet(ProtocolNumber.GPS_LOCATION, payload, serial_number)

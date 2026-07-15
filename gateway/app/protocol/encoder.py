"""Shim — encoder GT06 legado → Codec Classic (7878)."""

from datetime import UTC, datetime

from app.protocols.gt06.codec import Gt06Codec
from app.protocols.gt06.packets import START_BYTES_SHORT

_classic = Gt06Codec(protocol_name="gt06", start_marker=START_BYTES_SHORT)


def build_ack(protocol_number: int, serial_number: int) -> bytes:
    return _classic.encode_ack(protocol_number, serial_number)


def build_login_packet(imei: str, serial_number: int = 1) -> bytes:
    return _classic.encode_login(imei, serial_number)


def build_heartbeat_packet(
    serial_number: int = 2,
    terminal_info: int = 0x00,
    voltage: int = 0x06,
    gsm_signal: int = 0x04,
) -> bytes:
    return _classic.encode_heartbeat(
        serial_number=serial_number,
        terminal_info=terminal_info,
        voltage=voltage,
        gsm_signal=gsm_signal,
    )


def build_gps_packet(
    latitude: float,
    longitude: float,
    speed_kmh: float = 0.0,
    course: int = 0,
    gps_time: datetime | None = None,
    serial_number: int = 3,
    satellites: int = 8,
) -> bytes:
    return _classic.encode_gps(
        latitude=latitude,
        longitude=longitude,
        speed_kmh=speed_kmh,
        course=course,
        gps_time=gps_time or datetime.now(UTC),
        serial_number=serial_number,
        satellites=satellites,
    )

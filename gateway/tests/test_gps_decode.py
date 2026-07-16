"""Testes de conversão GPS GT06 (layout oficial 0x12/0x22)."""

from datetime import UTC, datetime

from app.protocols.gt06.utils import (
    decode_gps_coordinates,
    decode_gps_course,
    decode_gps_datetime,
    decode_gps_speed,
    encode_gps_course_status,
)


def _build_payload(
    *,
    lat: float,
    lon: float,
    speed: int = 0,
    course: int = 0,
    when: datetime | None = None,
    satellites: int = 8,
) -> bytes:
    now = when or datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
    dt = bytes([now.year % 100, now.month, now.day, now.hour, now.minute, now.second])
    gps_info = 0xC0 | (satellites & 0x0F)
    lat_raw = int(abs(lat) * 1_800_000)
    lon_raw = int(abs(lon) * 1_800_000)
    status = encode_gps_course_status(course, latitude=lat, longitude=lon)
    return (
        dt
        + bytes([gps_info])
        + lat_raw.to_bytes(4, "big")
        + lon_raw.to_bytes(4, "big")
        + bytes([speed])
        + status.to_bytes(2, "big")
    )


def test_official_packet_example_coordinates() -> None:
    # Exemplo do protocolo GT06 v1.8.1 (tabela GPS Information)
    payload = bytes.fromhex(
        "0B081D112E10"  # datetime
        "CF"  # length/satellites
        "027AC7EB"  # latitude
        "0C465849"  # longitude
        "00"  # speed
        "148F"  # course/status (North/East)
    )
    lat, lon = decode_gps_coordinates(payload)
    assert lat is not None and lon is not None
    assert -90 <= lat <= 90
    assert -180 <= lon <= 180
    assert abs(lat - (0x027AC7EB / 1_800_000)) < 1e-9
    assert abs(lon - (0x0C465849 / 1_800_000)) < 1e-9
    assert lat > 0
    assert lon > 0
    assert decode_gps_speed(payload) == 0.0
    assert decode_gps_course(payload) == (0x148F & 0x03FF)


def test_brazil_southwest_hemisphere() -> None:
    payload = _build_payload(lat=-23.550520, lon=-46.633308, speed=45, course=180)
    lat, lon = decode_gps_coordinates(payload)
    assert lat is not None and lon is not None
    assert abs(lat - (-23.550520)) < 1e-5
    assert abs(lon - (-46.633308)) < 1e-5
    assert decode_gps_speed(payload) == 45.0
    assert decode_gps_course(payload) == 180


def test_speed_stationary_and_moving() -> None:
    stopped = _build_payload(lat=-15.0, lon=-47.0, speed=0)
    slow = _build_payload(lat=-15.0, lon=-47.0, speed=2)
    fast = _build_payload(lat=-15.0, lon=-47.0, speed=120)
    assert decode_gps_speed(stopped) == 0.0
    assert decode_gps_speed(slow) == 2.0
    assert decode_gps_speed(fast) == 120.0


def test_gps_time_is_utc_binary_not_bcd() -> None:
    # 0x17 = 23 decimal (inválido como BCD) — confirma encoding binário
    payload = bytes.fromhex(
        "0A03170F3217"  # 2010-03-23 15:50:23 UTC (exemplo do manual)
        "C8"
        "026B3F3E"
        "0C465849"
        "00"
        "1400"
    )
    gps_time = decode_gps_datetime(payload)
    assert gps_time == datetime(2010, 3, 23, 15, 50, 23, tzinfo=UTC)


def test_rejects_out_of_range_coordinates() -> None:
    # raw propositalmente absurdo (simula offset errado antigo)
    payload = bytes.fromhex(
        "180101000000"
        "C8"
        "4555E0C4"  # ~646 degrees se dividido por 1.8e6
        "B1234567"
        "00"
        "1400"
    )
    lat, lon = decode_gps_coordinates(payload)
    assert lat is None and lon is None

from datetime import UTC, datetime

from app.contracts.messages import DeviceHeartbeat
from app.contracts.messages import SCHEMA_VERSION


def test_map_login() -> None:
    from app.domain.mapper import Gt06DomainMapper
    from app.protocol.encoder import build_login_packet
    from app.protocol.parser import parse_packet

    IMEI = "867686031234567"
    MAPPER = Gt06DomainMapper()
    packet = parse_packet(build_login_packet(IMEI))
    assert packet is not None
    msg = MAPPER.map_packet(
        packet, tracker_imei=None, connection_id="c1", remote_ip="127.0.0.1:5023", trace_id="t1"
    )
    assert msg is not None
    assert msg.message_type.value == "connection"
    assert msg.tracker_imei == IMEI
    assert msg.trace_id == "t1"
    assert msg.schema_version == SCHEMA_VERSION


def test_map_gps_position() -> None:
    from app.domain.mapper import Gt06DomainMapper
    from app.protocol.encoder import build_gps_packet
    from app.protocol.parser import parse_packet

    IMEI = "867686031234567"
    MAPPER = Gt06DomainMapper()
    packet = parse_packet(
        build_gps_packet(-23.550520, -46.633308, speed_kmh=45.0, course=180)
    )
    assert packet is not None
    msg = MAPPER.map_packet(
        packet, tracker_imei=IMEI, connection_id="c1", remote_ip="127.0.0.1"
    )
    assert msg is not None
    assert msg.message_type.value == "position"
    assert msg.latitude is not None
    assert msg.longitude is not None
    assert -90 <= msg.latitude <= 90
    assert -180 <= msg.longitude <= 180
    assert abs(msg.latitude - (-23.550520)) < 1e-5
    assert abs(msg.longitude - (-46.633308)) < 1e-5
    assert msg.speed_kmh == 45.0
    assert msg.course_degrees == 180
    assert msg.gps_time is not None
    assert msg.gps_time.tzinfo is not None
    assert msg.source_protocol == "gt06"
from app.protocol.encoder import build_gps_packet, build_heartbeat_packet, build_login_packet
from app.protocol.parser import extract_packets, parse_packet


IMEI = "867686031234567"


def test_login_roundtrip() -> None:
    packet = build_login_packet(IMEI, serial_number=1)
    frames, _ = extract_packets(bytearray(packet))
    assert len(frames) == 1
    parsed = parse_packet(frames[0])
    assert parsed is not None
    assert parsed.protocol_number == 0x01
    assert parsed.imei == IMEI
    assert parsed.serial_number == 1


def test_heartbeat_roundtrip() -> None:
    packet = build_heartbeat_packet(serial_number=2)
    parsed = parse_packet(packet)
    assert parsed is not None
    assert parsed.protocol_number == 0x13


def test_gps_roundtrip() -> None:
    packet = build_gps_packet(latitude=-23.550520, longitude=-46.633308, serial_number=3)
    parsed = parse_packet(packet)
    assert parsed is not None
    assert parsed.protocol_number == 0x12
    assert len(parsed.payload) >= 18


def test_invalid_packet_rejected() -> None:
    assert parse_packet(b"\x78\x78\x00") is None
    assert parse_packet(b"invalid") is None

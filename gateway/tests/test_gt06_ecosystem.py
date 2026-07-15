"""Testes do ecossistema GT06 (Classic + V2 + Codec + Decoder + CRC)."""

from __future__ import annotations

import pytest

from app.exceptions import CRCValidationError, InvalidPacketError
from app.protocols import ProtocolDetector, create_default_registry
from app.protocols.gt06.classic import GT06ClassicProtocol
from app.protocols.gt06.codec import Gt06Codec
from app.protocols.gt06.crc import crc16_x25
from app.protocols.gt06.decoder import PacketDecoder
from app.protocols.gt06.packets import (
    START_BYTES_LONG,
    START_BYTES_SHORT,
    PacketType,
    ProtocolNumber,
)
from app.protocols.gt06.v2 import GT06V2Protocol


IMEI = "867686031234567"


@pytest.fixture
def classic_codec() -> Gt06Codec:
    return Gt06Codec(protocol_name="gt06", start_marker=START_BYTES_SHORT)


@pytest.fixture
def v2_codec() -> Gt06Codec:
    return Gt06Codec(protocol_name="gt06_v2", start_marker=START_BYTES_LONG)


def test_classic_login(classic_codec: Gt06Codec) -> None:
    raw = classic_codec.encode_login(IMEI, serial_number=1)
    assert raw.startswith(START_BYTES_SHORT)
    packet = classic_codec.decode(raw)
    assert packet.packet_type == PacketType.LOGIN
    assert packet.protocol_number == ProtocolNumber.LOGIN
    assert packet.imei == IMEI
    assert packet.protocol == "gt06"


def test_classic_heartbeat(classic_codec: Gt06Codec) -> None:
    raw = classic_codec.encode_heartbeat(serial_number=2)
    packet = classic_codec.decode(raw)
    assert packet.packet_type == PacketType.HEARTBEAT
    assert packet.protocol_number == ProtocolNumber.HEARTBEAT


def test_classic_gps(classic_codec: Gt06Codec) -> None:
    raw = classic_codec.encode_gps(-23.550520, -46.633308, serial_number=3)
    packet = classic_codec.decode(raw)
    assert packet.packet_type == PacketType.GPS
    assert packet.protocol_number == ProtocolNumber.GPS_LOCATION
    assert len(packet.payload) >= 18


def test_v2_login(v2_codec: Gt06Codec) -> None:
    raw = v2_codec.encode_login(IMEI, serial_number=1)
    assert raw.startswith(START_BYTES_LONG)
    packet = v2_codec.decode(raw)
    assert packet.packet_type == PacketType.LOGIN
    assert packet.imei == IMEI
    assert packet.protocol == "gt06_v2"
    # Length field is 2 bytes
    assert raw[2:4] == packet.length.to_bytes(2, "big")


def test_v2_heartbeat(v2_codec: Gt06Codec) -> None:
    raw = v2_codec.encode_heartbeat(serial_number=2)
    packet = v2_codec.decode(raw)
    assert packet.packet_type == PacketType.HEARTBEAT
    assert raw.startswith(START_BYTES_LONG)


def test_v2_gps(v2_codec: Gt06Codec) -> None:
    raw = v2_codec.encode_gps(-23.55, -46.63, serial_number=3)
    packet = v2_codec.decode(raw)
    assert packet.packet_type == PacketType.GPS
    assert packet.protocol == "gt06_v2"


def test_crc_valid(classic_codec: Gt06Codec) -> None:
    raw = classic_codec.encode_login(IMEI)
    # CRC over length..serial must match
    packet = classic_codec.decode(raw)
    assert crc16_x25(raw[2 : 2 + 1 + packet.length - 2]) == packet.crc


def test_crc_invalid(classic_codec: Gt06Codec) -> None:
    raw = bytearray(classic_codec.encode_login(IMEI))
    # Flip a CRC byte
    raw[-3] ^= 0xFF
    with pytest.raises(CRCValidationError):
        classic_codec.decode(bytes(raw))


def test_incomplete_packet(classic_codec: Gt06Codec) -> None:
    raw = classic_codec.encode_login(IMEI)
    with pytest.raises(InvalidPacketError):
        classic_codec.decode(raw[:8])


def test_invalid_header(classic_codec: Gt06Codec) -> None:
    with pytest.raises(InvalidPacketError, match="Invalid start bytes"):
        classic_codec.decode(b"\x7e\x7e\x05\x01\x00\x01\x00\x00\x0d\x0a")


def test_packet_decoder_auto_detect(classic_codec: Gt06Codec, v2_codec: Gt06Codec) -> None:
    decoder = PacketDecoder()
    classic_raw = classic_codec.encode_login(IMEI)
    v2_raw = v2_codec.encode_login(IMEI)

    p1 = decoder.decode(classic_raw)
    p2 = decoder.decode(v2_raw)
    assert p1 is not None and p1.protocol == "gt06"
    assert p2 is not None and p2.protocol == "gt06_v2"
    assert decoder.decode(b"\x00\x01") is None


def test_codec_ack_roundtrip(classic_codec: Gt06Codec, v2_codec: Gt06Codec) -> None:
    classic_ack = classic_codec.encode_ack(ProtocolNumber.LOGIN, 1)
    v2_ack = v2_codec.encode_ack(ProtocolNumber.LOGIN, 1)
    assert classic_ack.startswith(START_BYTES_SHORT)
    assert v2_ack.startswith(START_BYTES_LONG)
    assert classic_codec.decode(classic_codec.encode_login(IMEI, 1)).serial_number == 1


def test_fingerprint_classic_and_v2() -> None:
    registry = create_default_registry()
    detector = ProtocolDetector(registry)

    assert detector.detect(b"\x78\x78\x0d\x01").name == "gt06"
    assert detector.detect(b"\x79\x79\x00\x10").name == "gt06_v2"
    assert registry.has_parser("gt06_v2") is True

    classic = GT06ClassicProtocol()
    v2 = GT06V2Protocol()
    assert isinstance(classic, type(classic))
    assert classic.has_parser and v2.has_parser


def test_v2_not_implemented_helpers() -> None:
    v2 = GT06V2Protocol()
    with pytest.raises(NotImplementedError):
        v2.encode_status()
    with pytest.raises(NotImplementedError):
        v2.encode_lbs()
    with pytest.raises(NotImplementedError):
        v2.codec.encode_command_response()


def test_legacy_app_protocol_compat() -> None:
    from app.protocol.encoder import build_login_packet
    from app.protocol.parser import extract_packets, parse_packet

    packet = build_login_packet(IMEI)
    frames, _ = extract_packets(bytearray(packet))
    parsed = parse_packet(frames[0])
    assert parsed is not None
    assert parsed.imei == IMEI

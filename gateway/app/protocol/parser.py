"""Shim — parser GT06 legado → Codec / Decoder da família GT06."""

from app.exceptions import CRCValidationError, InvalidPacketError
from app.protocols.gt06.codec import extract_frames
from app.protocols.gt06.decoder import PacketDecoder
from app.protocols.gt06.packets import (
    START_BYTES_LONG,
    START_BYTES_SHORT,
    Gt06Packet,
)

# Mantém comportamento legado: extrai Classic (7878) e V2 (7979).
_LEGACY_MARKERS = (START_BYTES_SHORT, START_BYTES_LONG)
_decoder = PacketDecoder()


def extract_packets(buffer: bytearray) -> tuple[list[bytes], bytearray]:
    return extract_frames(buffer, start_markers=_LEGACY_MARKERS)


def parse_packet(raw: bytes) -> Gt06Packet | None:
    try:
        return _parse_packet_or_raise(raw)
    except (CRCValidationError, InvalidPacketError):
        return None


def _parse_packet_or_raise(raw: bytes) -> Gt06Packet:
    return _decoder.decode_or_raise(raw)

"""Família de protocolos GT06 (Classic + V2)."""

from app.protocols.gt06.base import BaseGT06Protocol
from app.protocols.gt06.classic import GT06ClassicProtocol, GT06Protocol
from app.protocols.gt06.codec import Gt06Codec, extract_frames
from app.protocols.gt06.crc import crc16_x25
from app.protocols.gt06.decoder import PacketDecoder
from app.protocols.gt06.packets import (
    START_BYTES_LONG,
    START_BYTES_SHORT,
    STOP_BYTES,
    Gt06Packet,
    Packet,
    PacketType,
    ProtocolNumber,
)
from app.protocols.gt06.v2 import GT06V2Protocol

__all__ = [
    "BaseGT06Protocol",
    "GT06ClassicProtocol",
    "GT06Protocol",
    "GT06V2Protocol",
    "Gt06Codec",
    "Gt06Packet",
    "Packet",
    "PacketDecoder",
    "PacketType",
    "ProtocolNumber",
    "START_BYTES_LONG",
    "START_BYTES_SHORT",
    "STOP_BYTES",
    "crc16_x25",
    "extract_frames",
]

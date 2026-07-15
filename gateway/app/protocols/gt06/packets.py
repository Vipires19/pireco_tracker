"""Tipos e estruturas de pacote da família GT06."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


START_BYTES_SHORT = b"\x78\x78"
START_BYTES_LONG = b"\x79\x79"
STOP_BYTES = b"\x0d\x0a"


class ProtocolNumber(IntEnum):
    """Números de protocolo GT06 (byte de tipo na frame)."""

    LOGIN = 0x01
    GPS_LOCATION = 0x12
    HEARTBEAT = 0x13
    ALARM = 0x16
    GPS_LOCATION_4G = 0x22
    # Reservados / variantes frequentes
    STATUS = 0x23
    LBS = 0x18
    COMMAND_RESPONSE = 0x15


class PacketType(str, Enum):
    LOGIN = "login"
    HEARTBEAT = "heartbeat"
    GPS = "gps"
    ALARM = "alarm"
    STATUS = "status"
    LBS = "lbs"
    COMMAND_RESPONSE = "command_response"
    UNKNOWN = "unknown"


_PROTOCOL_TO_PACKET_TYPE: dict[int, PacketType] = {
    ProtocolNumber.LOGIN: PacketType.LOGIN,
    ProtocolNumber.GPS_LOCATION: PacketType.GPS,
    ProtocolNumber.GPS_LOCATION_4G: PacketType.GPS,
    ProtocolNumber.HEARTBEAT: PacketType.HEARTBEAT,
    ProtocolNumber.ALARM: PacketType.ALARM,
    ProtocolNumber.STATUS: PacketType.STATUS,
    ProtocolNumber.LBS: PacketType.LBS,
    ProtocolNumber.COMMAND_RESPONSE: PacketType.COMMAND_RESPONSE,
}


def packet_type_for(protocol_number: int) -> PacketType:
    return _PROTOCOL_TO_PACKET_TYPE.get(protocol_number, PacketType.UNKNOWN)


@dataclass(frozen=True)
class Packet:
    """Pacote GT06 decodificado (independente do transporte TCP)."""

    protocol: str
    packet_type: PacketType
    payload: bytes
    crc: int
    length: int
    protocol_number: int
    serial_number: int
    raw: bytes
    start_marker: bytes
    imei: str | None = None


# Alias de compatibilidade com o mapper / testes legados.
Gt06Packet = Packet

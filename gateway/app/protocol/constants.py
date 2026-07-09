"""Constantes do protocolo GT06."""

from enum import IntEnum

START_BYTES_SHORT = b"\x78\x78"
START_BYTES_LONG = b"\x79\x79"
STOP_BYTES = b"\x0d\x0a"


class ProtocolNumber(IntEnum):
    LOGIN = 0x01
    GPS_LOCATION = 0x12
    HEARTBEAT = 0x13
    ALARM = 0x16
    GPS_LOCATION_4G = 0x22

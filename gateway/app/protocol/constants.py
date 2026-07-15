"""Shim — constantes GT06 legadas → protocols.gt06.packets."""

from app.protocols.gt06.packets import (
    START_BYTES_LONG,
    START_BYTES_SHORT,
    STOP_BYTES,
    ProtocolNumber,
)

__all__ = [
    "START_BYTES_LONG",
    "START_BYTES_SHORT",
    "STOP_BYTES",
    "ProtocolNumber",
]

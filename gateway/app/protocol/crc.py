"""Shim — crc GT06 legado → protocols.gt06.crc."""

from app.protocols.gt06.crc import crc16_x25, verify_crc

__all__ = ["crc16_x25", "verify_crc"]

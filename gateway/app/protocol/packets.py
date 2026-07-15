"""Shim — estruturas GT06 legadas → protocols.gt06."""

from app.protocols.gt06.packets import Gt06Packet, Packet, PacketType, ProtocolNumber
from app.protocols.gt06.utils import (
    bcd_to_imei,
    decode_gps_coordinates,
    decode_gps_course,
    decode_gps_datetime,
    decode_gps_speed,
    decode_login_imei,
    imei_to_bcd,
    packet_category,
)

__all__ = [
    "Gt06Packet",
    "Packet",
    "PacketType",
    "ProtocolNumber",
    "bcd_to_imei",
    "decode_gps_coordinates",
    "decode_gps_course",
    "decode_gps_datetime",
    "decode_gps_speed",
    "decode_login_imei",
    "imei_to_bcd",
    "packet_category",
]

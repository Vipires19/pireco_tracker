"""Codec GT06 — encoding e decoding centralizados (sem montagem manual nos parsers)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.exceptions import CRCValidationError, InvalidPacketError
from app.protocols.gt06.crc import crc16_x25
from app.protocols.gt06.packets import (
    START_BYTES_LONG,
    START_BYTES_SHORT,
    STOP_BYTES,
    Packet,
    ProtocolNumber,
    packet_type_for,
)
from app.protocols.gt06.utils import decode_login_imei, encode_gps_course_status, imei_to_bcd


class Gt06Codec:
    """Encoding / decoding da envelope GT06 (Classic 7878 e V2 7979)."""

    def __init__(self, *, protocol_name: str, start_marker: bytes) -> None:
        if start_marker not in (START_BYTES_SHORT, START_BYTES_LONG):
            raise ValueError(f"Unsupported start marker: {start_marker!r}")
        self.protocol_name = protocol_name
        self.start_marker = start_marker
        self._length_size = 1 if start_marker == START_BYTES_SHORT else 2

    # --- Decoding ---

    def decode(self, raw: bytes) -> Packet:
        """Decodifica um frame completo; levanta CRCValidationError / InvalidPacketError."""
        if len(raw) < 10:
            raise InvalidPacketError("Packet too short", details={"size": len(raw)})

        if not raw.startswith(self.start_marker):
            raise InvalidPacketError("Invalid start bytes")

        if not raw.endswith(STOP_BYTES):
            raise InvalidPacketError("Missing stop bytes")

        if self._length_size == 1:
            packet_length = raw[2]
            data_start = 3
        else:
            packet_length = int.from_bytes(raw[2:4], "big")
            data_start = 4

        data_end = data_start + packet_length - 2
        if data_end + 4 > len(raw):
            raise InvalidPacketError("Truncated packet")

        protocol_number = raw[data_start]
        payload_end = data_end - 2
        payload = raw[data_start + 1 : payload_end]
        serial_number = int.from_bytes(raw[payload_end:data_end], "big")
        received_crc = int.from_bytes(raw[data_end : data_end + 2], "big")

        if crc16_x25(raw[2:data_end]) != received_crc:
            raise CRCValidationError("CRC mismatch")

        imei = None
        if protocol_number == ProtocolNumber.LOGIN:
            imei = decode_login_imei(payload)

        return Packet(
            protocol=self.protocol_name,
            packet_type=packet_type_for(protocol_number),
            payload=payload,
            crc=received_crc,
            length=packet_length,
            protocol_number=protocol_number,
            serial_number=serial_number,
            raw=raw,
            start_marker=self.start_marker,
            imei=imei,
        )

    def try_decode(self, raw: bytes) -> Packet | None:
        try:
            return self.decode(raw)
        except (CRCValidationError, InvalidPacketError):
            return None

    # --- Encoding ---

    def encode_ack(self, protocol_number: int, serial_number: int) -> bytes:
        """ACK do servidor — mesmo formato de produção Classic; V2 usa length de 2 bytes."""
        if self._length_size == 1:
            body = bytes([0x05, protocol_number]) + serial_number.to_bytes(2, "big")
            crc = crc16_x25(body)
            return self.start_marker + body + crc.to_bytes(2, "big") + STOP_BYTES

        # V2 (7979): Packet Length em 2 bytes.
        length_bytes = (0x0005).to_bytes(2, "big")
        content = bytes([protocol_number]) + serial_number.to_bytes(2, "big")
        crc_data = length_bytes + content
        crc = crc16_x25(crc_data)
        return self.start_marker + crc_data + crc.to_bytes(2, "big") + STOP_BYTES

    def encode_packet(self, protocol_number: int, payload: bytes, serial_number: int) -> bytes:
        serial_bytes = serial_number.to_bytes(2, "big")
        content = bytes([protocol_number]) + payload + serial_bytes
        length = len(content) + 2  # + CRC
        if self._length_size == 1:
            if length > 0xFF:
                raise ValueError("Classic packet length exceeds 1 byte; use GT06 V2")
            length_bytes = bytes([length])
        else:
            length_bytes = length.to_bytes(2, "big")

        crc_data = length_bytes + content
        crc = crc16_x25(crc_data)
        return self.start_marker + crc_data + crc.to_bytes(2, "big") + STOP_BYTES

    def encode_login(self, imei: str, serial_number: int = 1) -> bytes:
        return self.encode_packet(ProtocolNumber.LOGIN, imei_to_bcd(imei), serial_number)

    def encode_heartbeat(
        self,
        serial_number: int = 2,
        terminal_info: int = 0x00,
        voltage: int = 0x06,
        gsm_signal: int = 0x04,
    ) -> bytes:
        payload = bytes([terminal_info, voltage, gsm_signal])
        return self.encode_packet(ProtocolNumber.HEARTBEAT, payload, serial_number)

    def encode_gps(
        self,
        latitude: float,
        longitude: float,
        speed_kmh: float = 0.0,
        course: int = 0,
        gps_time: datetime | None = None,
        serial_number: int = 3,
        satellites: int = 8,
    ) -> bytes:
        now = gps_time or datetime.now(UTC)
        datetime_bytes = bytes(
            [
                now.year % 100,
                now.month,
                now.day,
                now.hour,
                now.minute,
                now.second,
            ]
        )
        lat_raw = int(abs(latitude) * 1_800_000)
        lon_raw = int(abs(longitude) * 1_800_000)
        # 1 byte: high nibble = GPS info length (12), low nibble = satellites
        gps_info = 0xC0 | (satellites & 0x0F)
        course_status = encode_gps_course_status(course, latitude=latitude, longitude=longitude)
        payload = (
            datetime_bytes
            + bytes([gps_info])
            + lat_raw.to_bytes(4, "big")
            + lon_raw.to_bytes(4, "big")
            + bytes([min(int(speed_kmh), 255)])
            + course_status.to_bytes(2, "big")
        )
        return self.encode_packet(ProtocolNumber.GPS_LOCATION, payload, serial_number)

    def encode_status(self, *_args, **_kwargs) -> bytes:
        raise NotImplementedError("GT06 STATUS encoder not implemented")

    def encode_lbs(self, *_args, **_kwargs) -> bytes:
        raise NotImplementedError("GT06 LBS encoder not implemented")

    def encode_command_response(self, *_args, **_kwargs) -> bytes:
        raise NotImplementedError("GT06 COMMAND_RESPONSE encoder not implemented")


def extract_frames(
    buffer: bytearray | bytes,
    *,
    start_markers: tuple[bytes, ...] = (START_BYTES_SHORT, START_BYTES_LONG),
) -> tuple[list[bytes], bytearray]:
    """Extrai frames completos do buffer para os start markers informados."""
    buf = buffer if isinstance(buffer, bytearray) else bytearray(buffer)
    packets: list[bytes] = []
    offset = 0

    while offset < len(buf):
        found: list[tuple[int, bytes]] = []
        for marker in start_markers:
            idx = buf.find(marker, offset)
            if idx != -1:
                found.append((idx, marker))

        if not found:
            break

        start_idx, start_marker = min(found, key=lambda item: item[0])
        length_size = 1 if start_marker == START_BYTES_SHORT else 2

        if start_idx + 2 + length_size > len(buf):
            break

        if length_size == 1:
            packet_length = buf[start_idx + 2]
            header_size = 2 + 1
        else:
            packet_length = int.from_bytes(buf[start_idx + 2 : start_idx + 4], "big")
            header_size = 2 + 2

        total_size = header_size + packet_length + 2
        if start_idx + total_size > len(buf):
            break

        frame = bytes(buf[start_idx : start_idx + total_size])
        if not frame.endswith(STOP_BYTES):
            offset = start_idx + 2
            continue

        packets.append(frame)
        offset = start_idx + total_size

    return packets, bytearray(buf[offset:])

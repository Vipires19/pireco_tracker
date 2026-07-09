"""Parser GT06 com exceções específicas."""

from app.exceptions import CRCValidationError, InvalidPacketError

from app.protocol.constants import START_BYTES_LONG, START_BYTES_SHORT, STOP_BYTES, ProtocolNumber
from app.protocol.crc import crc16_x25
from app.protocol.packets import Gt06Packet, decode_login_imei


def extract_packets(buffer: bytearray) -> tuple[list[bytes], bytearray]:
    packets: list[bytes] = []
    offset = 0

    while offset < len(buffer):
        start_idx = buffer.find(START_BYTES_SHORT, offset)
        long_idx = buffer.find(START_BYTES_LONG, offset)

        if start_idx == -1 and long_idx == -1:
            break

        if start_idx == -1 or (long_idx != -1 and long_idx < start_idx):
            start_idx = long_idx
            start_marker = START_BYTES_LONG
            length_size = 2
        else:
            start_marker = START_BYTES_SHORT
            length_size = 1

        if start_idx + 2 + length_size > len(buffer):
            break

        if start_marker == START_BYTES_SHORT:
            packet_length = buffer[start_idx + 2]
            header_size = 2 + 1
        else:
            packet_length = int.from_bytes(buffer[start_idx + 2 : start_idx + 4], "big")
            header_size = 2 + 2

        total_size = header_size + packet_length + 2

        if start_idx + total_size > len(buffer):
            break

        frame = bytes(buffer[start_idx : start_idx + total_size])
        if not frame.endswith(STOP_BYTES):
            offset = start_idx + 2
            continue

        packets.append(frame)
        offset = start_idx + total_size

    return packets, bytearray(buffer[offset:])


def parse_packet(raw: bytes) -> Gt06Packet | None:
    try:
        return _parse_packet_or_raise(raw)
    except (CRCValidationError, InvalidPacketError):
        return None


def _parse_packet_or_raise(raw: bytes) -> Gt06Packet:
    if len(raw) < 10:
        raise InvalidPacketError("Packet too short", details={"size": len(raw)})

    if raw.startswith(START_BYTES_SHORT):
        start_marker = START_BYTES_SHORT
        packet_length = raw[2]
        data_start = 3
    elif raw.startswith(START_BYTES_LONG):
        start_marker = START_BYTES_LONG
        packet_length = int.from_bytes(raw[2:4], "big")
        data_start = 4
    else:
        raise InvalidPacketError("Invalid start bytes")

    if not raw.endswith(STOP_BYTES):
        raise InvalidPacketError("Missing stop bytes")

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

    return Gt06Packet(
        start_marker=start_marker,
        length=packet_length,
        protocol_number=protocol_number,
        payload=payload,
        serial_number=serial_number,
        crc=received_crc,
        raw=raw,
        imei=imei,
    )

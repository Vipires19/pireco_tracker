"""CRC-ITU (X25) — única implementação CRC da família GT06."""


def crc16_x25(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
    return (~crc) & 0xFFFF


def verify_crc(data: bytes, expected: int) -> bool:
    return crc16_x25(data) == expected

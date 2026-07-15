"""Helpers de formatação para logs de bytes (HEX/ASCII)."""


def bytes_to_hex(data: bytes) -> str:
    return data.hex()


def bytes_to_ascii(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)

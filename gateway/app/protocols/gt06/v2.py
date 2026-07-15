"""GT06 V2 — header 0x7979 (pacotes estendidos)."""

from __future__ import annotations

from typing import Any, ClassVar

from app.protocols.gt06.base import BaseGT06Protocol
from app.protocols.gt06.packets import START_BYTES_LONG, PacketType


class GT06V2Protocol(BaseGT06Protocol):
    """
    Implementação V2 (7979).

    Login / Heartbeat / GPS / ACK usam o Codec compartilhado.
    Tipos ainda sem especificação completa levantam NotImplementedError.
    """

    SIGNATURES: ClassVar[tuple[bytes, ...]] = (START_BYTES_LONG,)
    SIGNATURE_REASON: ClassVar[str] = "Header GT06 V2"
    START_MARKER: ClassVar[bytes] = START_BYTES_LONG

    @property
    def name(self) -> str:
        return "gt06_v2"

    def encode_status(self, *args: Any, **kwargs: Any) -> bytes:
        raise NotImplementedError("GT06 V2 STATUS packet structure not fully specified")

    def encode_lbs(self, *args: Any, **kwargs: Any) -> bytes:
        raise NotImplementedError("GT06 V2 LBS packet structure not fully specified")

    def encode_command_response(self, *args: Any, **kwargs: Any) -> bytes:
        raise NotImplementedError(
            "GT06 V2 COMMAND_RESPONSE packet structure not fully specified"
        )

    def decode_extended_type(self, packet_type: PacketType, payload: bytes) -> Any:
        if packet_type in (PacketType.STATUS, PacketType.LBS, PacketType.COMMAND_RESPONSE):
            raise NotImplementedError(
                f"GT06 V2 decoder for {packet_type.value} not fully specified"
            )
        return None

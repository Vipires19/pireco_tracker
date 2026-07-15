"""Packet Decoder — parsing independente da comunicação TCP."""

from __future__ import annotations

from app.protocols.gt06.codec import Gt06Codec
from app.protocols.gt06.packets import (
    START_BYTES_LONG,
    START_BYTES_SHORT,
    Packet,
)


class PacketDecoder:
    """
    Recebe bytes e devolve Packet.

    Detecta Classic (7878) ou V2 (7979) pelo cabeçalho quando o codec
    não é forçado.
    """

    def __init__(
        self,
        *,
        protocol_name: str | None = None,
        start_marker: bytes | None = None,
    ) -> None:
        self._protocol_name = protocol_name
        self._start_marker = start_marker

    def decode(self, data: bytes) -> Packet | None:
        codec = self._resolve_codec(data)
        if codec is None:
            return None
        return codec.try_decode(data)

    def decode_or_raise(self, data: bytes) -> Packet:
        codec = self._resolve_codec(data)
        if codec is None:
            from app.exceptions import InvalidPacketError

            raise InvalidPacketError("Invalid start bytes")
        return codec.decode(data)

    def _resolve_codec(self, data: bytes) -> Gt06Codec | None:
        if self._start_marker is not None and self._protocol_name is not None:
            return Gt06Codec(protocol_name=self._protocol_name, start_marker=self._start_marker)

        if data.startswith(START_BYTES_SHORT):
            return Gt06Codec(
                protocol_name=self._protocol_name or "gt06",
                start_marker=START_BYTES_SHORT,
            )
        if data.startswith(START_BYTES_LONG):
            return Gt06Codec(
                protocol_name=self._protocol_name or "gt06_v2",
                start_marker=START_BYTES_LONG,
            )
        return None

"""Interface comum para protocolos de rastreamento TCP."""

from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import StreamReader, StreamWriter
from typing import Any, ClassVar


class BaseProtocol(ABC):
    """Contrato que toda implementação de protocolo deve seguir."""

    # Assinaturas binárias dos primeiros bytes. O Fingerprint Engine as coleta
    # automaticamente via Registry — não é necessário alterar o Fingerprint.
    SIGNATURES: ClassVar[tuple[bytes, ...]] = ()
    SIGNATURE_REASON: ClassVar[str] = ""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador estável do protocolo (ex.: \"gt06\")."""

    @property
    def has_parser(self) -> bool:
        """True quando existe implementação capaz de tratar a conexão."""
        return True

    @abstractmethod
    def match(self, data: bytes) -> bool:
        """Retorna True se os bytes iniciais forem compatíveis com este protocolo."""

    @abstractmethod
    def parse_packet(self, raw: bytes) -> Any:
        """Parseia um frame bruto no modelo interno do protocolo."""

    @abstractmethod
    def build_ack(self, *args: Any, **kwargs: Any) -> bytes:
        """Monta a resposta ACK adequada ao pacote processado."""

    @abstractmethod
    async def handle_connection(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        *,
        connection_id: str,
        remote_ip: str,
        lifecycle: Any,
        initial_buffer: bytes | bytearray,
        remote_port: int = 0,
    ) -> None:
        """Processa a conexão TCP já associada a este protocolo."""

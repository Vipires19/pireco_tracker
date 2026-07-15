"""GT06 Classic — header 0x7878 (comportamento legado preservado)."""

from __future__ import annotations

from typing import ClassVar

from app.protocols.gt06.base import BaseGT06Protocol
from app.protocols.gt06.packets import START_BYTES_SHORT


class GT06ClassicProtocol(BaseGT06Protocol):
    """Implementação Classic (7878) da família GT06."""

    SIGNATURES: ClassVar[tuple[bytes, ...]] = (START_BYTES_SHORT,)
    SIGNATURE_REASON: ClassVar[str] = "Header GT06 Classic"
    START_MARKER: ClassVar[bytes] = START_BYTES_SHORT

    @property
    def name(self) -> str:
        return "gt06"


# Compatibilidade com imports anteriores.
GT06Protocol = GT06ClassicProtocol

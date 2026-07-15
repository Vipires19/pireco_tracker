"""Registro de protocolos suportados pelo Gateway."""

from __future__ import annotations

from app.protocols.base import BaseProtocol
from app.protocols.fingerprint import ProtocolMatch

UNKNOWN_PROTOCOL_NAME = "unknown"


class ProtocolRegistry:
    """
    Registra, lista e localiza implementações de BaseProtocol.

    Mantém cache em memória das assinaturas para o Fingerprint Engine (O(n)).
    """

    def __init__(self) -> None:
        self._protocols: dict[str, BaseProtocol] = {}
        # Cache: (signature_bytes, protocol_name, reason)
        self._signature_cache: list[tuple[bytes, str, str]] = []

    def register(self, protocol: BaseProtocol) -> None:
        name = protocol.name
        if name in self._protocols:
            raise ValueError(f"Protocol already registered: {name}")
        self._protocols[name] = protocol
        self._rebuild_signature_cache()

    def _rebuild_signature_cache(self) -> None:
        entries: list[tuple[bytes, str, str]] = []
        for protocol in self._protocols.values():
            if protocol.name == UNKNOWN_PROTOCOL_NAME:
                continue
            reason = protocol.SIGNATURE_REASON or f"Assinatura {protocol.name}"
            for signature in protocol.SIGNATURES:
                entries.append((signature, protocol.name, reason))
        entries.sort(key=lambda item: len(item[0]), reverse=True)
        self._signature_cache = entries

    def signature_entries(self) -> list[tuple[bytes, str, str]]:
        return self._signature_cache

    def has_parser(self, protocol_name: str) -> bool:
        protocol = self._protocols.get(protocol_name)
        if protocol is None:
            return False
        return bool(protocol.has_parser)

    def resolve(self, match: ProtocolMatch) -> BaseProtocol:
        unknown = self._protocols.get(UNKNOWN_PROTOCOL_NAME)
        if unknown is None:
            raise RuntimeError("UnknownProtocol not registered")

        if match.protocol_name == UNKNOWN_PROTOCOL_NAME:
            return unknown

        protocol = self._protocols.get(match.protocol_name)
        if protocol is None or not protocol.has_parser:
            return unknown

        return protocol

    def decision_reason(self, match: ProtocolMatch, resolved: BaseProtocol) -> str:
        if match.protocol_name == UNKNOWN_PROTOCOL_NAME:
            return match.reason
        if resolved.name == UNKNOWN_PROTOCOL_NAME and match.protocol_name != UNKNOWN_PROTOCOL_NAME:
            return "Parser não implementado"
        return match.reason

    def list(self) -> list[BaseProtocol]:
        return list(self._protocols.values())

    def get(self, name: str) -> BaseProtocol | None:
        return self._protocols.get(name)

    def names(self) -> list[str]:
        return list(self._protocols.keys())

    @property
    def count(self) -> int:
        return len(self._protocols)


def create_default_registry() -> ProtocolRegistry:
    """Registry padrão: GT06 Classic, GT06 V2 e Unknown."""
    from app.protocols.gt06.classic import GT06ClassicProtocol
    from app.protocols.gt06.v2 import GT06V2Protocol
    from app.protocols.unknown.protocol import UnknownProtocol

    registry = ProtocolRegistry()
    registry.register(GT06ClassicProtocol())
    registry.register(GT06V2Protocol())
    registry.register(UnknownProtocol())
    return registry

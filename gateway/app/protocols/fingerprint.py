"""Fingerprint Engine — identificação de protocolo pelos primeiros bytes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class _SignatureSource(Protocol):
    def signature_entries(self) -> list[tuple[bytes, str, str]]: ...


@dataclass(frozen=True)
class ProtocolMatch:
    """Resultado da identificação por fingerprint."""

    protocol_name: str
    confidence: int
    matched_signature: str
    first_bytes: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol_name,
            "confidence": self.confidence,
            "signature": self.matched_signature,
            "first_bytes": self.first_bytes,
            "reason": self.reason,
        }

    def as_log_fields(self) -> dict[str, Any]:
        return {
            "event": "FINGERPRINT",
            "signature": self.matched_signature,
            "protocol": self.protocol_name,
            "confidence": self.confidence,
            "first_bytes": self.first_bytes,
            "reason": self.reason,
        }


class FingerprintEngine:
    """
    Descobre o protocolo a partir das assinaturas em cache do Registry.

    Complexidade O(n) sobre as assinaturas registradas.
    Não usa reflexão nem import dinâmico por conexão.
    """

    def __init__(self, registry: _SignatureSource) -> None:
        self._registry = registry

    def identify(self, data: bytes) -> ProtocolMatch:
        peek = data[:16].hex() if data else ""

        if not data:
            return ProtocolMatch(
                protocol_name="unknown",
                confidence=0,
                matched_signature="",
                first_bytes="",
                reason="Sem bytes para identificar",
            )

        # O(n) sobre assinaturas em cache (memória).
        for signature, protocol_name, reason in self._registry.signature_entries():
            if len(data) < len(signature):
                continue
            if data.startswith(signature):
                return ProtocolMatch(
                    protocol_name=protocol_name,
                    confidence=100,
                    matched_signature=signature.hex(),
                    first_bytes=data[: len(signature)].hex(),
                    reason=reason,
                )

        return ProtocolMatch(
            protocol_name="unknown",
            confidence=0,
            matched_signature="",
            first_bytes=peek,
            reason="Nenhuma assinatura conhecida",
        )

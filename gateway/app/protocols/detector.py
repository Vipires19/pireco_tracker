"""Detecção de protocolo via Fingerprint Engine + Registry."""

from __future__ import annotations

import logging

from app.core.observability import get_logger, log_with_fields
from app.protocols.base import BaseProtocol
from app.protocols.fingerprint import FingerprintEngine, ProtocolMatch
from app.protocols.registry import UNKNOWN_PROTOCOL_NAME, ProtocolRegistry

logger = get_logger(__name__)

# Mínimo para distinguir cabeçalhos típicos (ex.: GT06 0x7878 / 0x7979).
MIN_DETECT_BYTES = 2


class ProtocolDetector:
    """
    Fluxo: primeiros bytes → Fingerprint Engine → Registry → instância.
    """

    def __init__(self, registry: ProtocolRegistry) -> None:
        self._registry = registry
        self._fingerprint = FingerprintEngine(registry)

    @property
    def fingerprint(self) -> FingerprintEngine:
        return self._fingerprint

    def identify(self, data: bytes) -> ProtocolMatch:
        """Apenas executa o Fingerprint Engine (sem resolver parser)."""
        return self._fingerprint.identify(data)

    def detect(self, data: bytes) -> BaseProtocol | None:
        """
        Identifica e resolve o protocolo que deve handle_connection.

        - Sem bytes suficientes → None (continuar lendo)
        - Assinatura conhecida + parser → protocolo concreto
        - Assinatura conhecida sem parser → Unknown (Learning Mode)
        - Assinatura desconhecida → Unknown (Learning Mode)
        """
        if not data:
            return None

        if len(data) < MIN_DETECT_BYTES:
            return None

        match = self._fingerprint.identify(data)
        resolved = self._registry.resolve(match)
        decision = resolved.name
        decision_reason = self._registry.decision_reason(match, resolved)

        log_with_fields(
            logger,
            logging.INFO,
            "Fingerprint detected",
            **match.as_log_fields(),
            decision=decision,
            decision_reason=decision_reason,
            learning_mode=decision == UNKNOWN_PROTOCOL_NAME,
        )

        return resolved

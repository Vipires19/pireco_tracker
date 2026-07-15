"""Camada de protocolos extensíveis do Gateway."""

from app.protocols.base import BaseProtocol
from app.protocols.detector import ProtocolDetector
from app.protocols.fingerprint import FingerprintEngine, ProtocolMatch
from app.protocols.registry import ProtocolRegistry, create_default_registry

__all__ = [
    "BaseProtocol",
    "FingerprintEngine",
    "ProtocolDetector",
    "ProtocolMatch",
    "ProtocolRegistry",
    "create_default_registry",
]

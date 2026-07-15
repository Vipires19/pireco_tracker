"""Variant Database — variantes de protocolos conhecidos."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ProtocolVariant:
    name: str
    parent_protocol: str
    differences: list[str] = field(default_factory=list)
    known_headers: list[str] = field(default_factory=list)
    known_crc: list[str] = field(default_factory=list)
    known_commands: list[str] = field(default_factory=list)
    known_ack: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_VARIANTS: list[ProtocolVariant] = [
    ProtocolVariant(
        name="gt06_classic",
        parent_protocol="gt06",
        differences=["Header 1 byte length"],
        known_headers=["7878"],
        known_crc=["crc16_x25"],
        known_commands=["LOGIN", "HEARTBEAT", "GPS"],
        known_ack=["787805{proto}{serial}{crc}0d0a"],
        notes="GT06 Classic",
    ),
    ProtocolVariant(
        name="gt06_v2",
        parent_protocol="gt06",
        differences=["Header 7979", "Length 2 bytes"],
        known_headers=["7979"],
        known_crc=["crc16_x25"],
        known_commands=["LOGIN", "HEARTBEAT", "GPS"],
        known_ack=["79790005{proto}{serial}{crc}0d0a"],
        notes="GT06 V2 / extended frames",
    ),
]


class VariantDatabase:
    def __init__(self, variants: list[ProtocolVariant] | None = None) -> None:
        self._items: dict[str, ProtocolVariant] = {}
        for item in variants or DEFAULT_VARIANTS:
            self.register(item)

    def register(self, variant: ProtocolVariant) -> None:
        self._items[variant.name] = variant

    def get(self, name: str) -> ProtocolVariant | None:
        return self._items.get(name)

    def by_parent(self, parent_protocol: str) -> list[ProtocolVariant]:
        return [v for v in self._items.values() if v.parent_protocol == parent_protocol]

    def by_header(self, header_hex: str) -> list[ProtocolVariant]:
        needle = header_hex.lower()
        return [v for v in self._items.values() if needle in [h.lower() for h in v.known_headers]]

    def list(self) -> list[ProtocolVariant]:
        return list(self._items.values())

"""Fabricantes conhecidos na Device Knowledge Base."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Manufacturer:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    country: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_MANUFACTURERS: list[Manufacturer] = [
    Manufacturer(id="concox", name="Concox", aliases=["Shenzhen Concox", "Jimi"], country="CN"),
    Manufacturer(id="jimi", name="Jimi IoT", aliases=["Concox", "Jimi"], country="CN"),
    Manufacturer(id="teltonika", name="Teltonika", aliases=[], country="LT"),
    Manufacturer(id="queclink", name="Queclink", aliases=[], country="CN"),
    Manufacturer(id="unknown", name="Unknown", aliases=[], notes="Fabricante não identificado"),
]


class ManufacturerRegistry:
    def __init__(self, manufacturers: list[Manufacturer] | None = None) -> None:
        self._items: dict[str, Manufacturer] = {}
        for item in manufacturers or DEFAULT_MANUFACTURERS:
            self.register(item)

    def register(self, manufacturer: Manufacturer) -> None:
        self._items[manufacturer.id] = manufacturer

    def get(self, manufacturer_id: str) -> Manufacturer | None:
        return self._items.get(manufacturer_id)

    def find_by_name(self, name: str) -> list[Manufacturer]:
        needle = name.strip().lower()
        return [
            m
            for m in self._items.values()
            if needle == m.name.lower() or needle == m.id or needle in [a.lower() for a in m.aliases]
        ]

    def list(self) -> list[Manufacturer]:
        return list(self._items.values())

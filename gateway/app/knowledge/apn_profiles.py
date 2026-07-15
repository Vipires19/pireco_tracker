"""APN Profiles — catálogo de APNs conhecidas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ApnProfile:
    id: str
    operator: str
    apn: str
    username: str | None = None
    password: str | None = None
    firmwares: list[str] = field(default_factory=list)
    manufacturers: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_APN_PROFILES: list[ApnProfile] = [
    ApnProfile(
        id="vivo_zap",
        operator="Vivo",
        apn="zap.vivo.com.br",
        username="vivo",
        password="vivo",
        firmwares=["generic"],
        manufacturers=["concox", "jimi"],
        notes="APN padrão Vivo Brasil",
    ),
    ApnProfile(
        id="claro_gprs",
        operator="Claro",
        apn="claro.com.br",
        username="claro",
        password="claro",
        firmwares=["generic"],
        manufacturers=["concox", "jimi"],
    ),
    ApnProfile(
        id="tim_brasil",
        operator="TIM",
        apn="timbrasil.br",
        username="tim",
        password="tim",
        firmwares=["generic"],
        manufacturers=["concox"],
    ),
]


class ApnCatalog:
    def __init__(self, profiles: list[ApnProfile] | None = None) -> None:
        self._items: dict[str, ApnProfile] = {}
        for profile in profiles or DEFAULT_APN_PROFILES:
            self.register(profile)

    def register(self, profile: ApnProfile) -> None:
        self._items[profile.id] = profile

    def get(self, profile_id: str) -> ApnProfile | None:
        return self._items.get(profile_id)

    def by_operator(self, operator: str) -> list[ApnProfile]:
        needle = operator.strip().lower()
        return [p for p in self._items.values() if p.operator.lower() == needle]

    def by_manufacturer(self, manufacturer: str) -> list[ApnProfile]:
        needle = manufacturer.lower()
        return [p for p in self._items.values() if needle in [m.lower() for m in p.manufacturers]]

    def list(self) -> list[ApnProfile]:
        return list(self._items.values())

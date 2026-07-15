"""SMS Knowledge — catálogo de comandos SMS por fabricante/família."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SmsCommand:
    command: str
    description: str
    parameters: list[str] = field(default_factory=list)
    firmware: str | None = None
    manufacturer: str | None = None
    families: list[str] = field(default_factory=list)
    notes: str | None = None
    example: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_SMS_COMMANDS: list[SmsCommand] = [
    SmsCommand(
        command="SERVER",
        description="Configura IP/porta do servidor",
        parameters=["mode", "ip", "port", "flag"],
        manufacturer="jimi",
        families=["J16 Ultra", "J16 Pro", "J16"],
        example="SERVER,0,IP,PORT,0#",
        notes="Formato comum em família J16",
    ),
    SmsCommand(
        command="APN",
        description="Configura APN da operadora",
        parameters=["apn", "user", "password"],
        manufacturer="concox",
        families=["GT06", "J16"],
        example="APN,zap.vivo.com.br#",
    ),
    SmsCommand(
        command="RESET",
        description="Reinicia o dispositivo",
        parameters=[],
        manufacturer="concox",
        families=["GT06", "J16"],
        example="RESET#",
    ),
    SmsCommand(
        command="STATUS",
        description="Solicita status do dispositivo",
        parameters=[],
        manufacturer="concox",
        families=["GT06"],
        example="STATUS#",
    ),
]


class SmsKnowledge:
    def __init__(self, commands: list[SmsCommand] | None = None) -> None:
        self._commands: list[SmsCommand] = list(commands or DEFAULT_SMS_COMMANDS)

    def register(self, command: SmsCommand) -> None:
        self._commands.append(command)

    def list(self) -> list[SmsCommand]:
        return list(self._commands)

    def find(
        self,
        *,
        command: str | None = None,
        manufacturer: str | None = None,
        family: str | None = None,
    ) -> list[SmsCommand]:
        results = self._commands
        if command:
            needle = command.upper()
            results = [c for c in results if c.command.upper() == needle]
        if manufacturer:
            m = manufacturer.lower()
            results = [c for c in results if (c.manufacturer or "").lower() == m]
        if family:
            f = family.lower()
            results = [
                c
                for c in results
                if f in [fam.lower() for fam in c.families] or any(f in fam.lower() for fam in c.families)
            ]
        return results

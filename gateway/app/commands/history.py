"""Histórico imutável de comandos (nunca apaga)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.commands.models import CommandRecord


class CommandHistory:
    def __init__(self) -> None:
        self._all: list[CommandRecord] = []
        self._by_device: dict[str, list[CommandRecord]] = defaultdict(list)
        self._by_id: dict[str, CommandRecord] = {}

    def append(self, record: CommandRecord) -> None:
        # Snapshot lógica: armazena a referência viva; to_dict congela visão.
        if record.command_id not in self._by_id:
            self._all.append(record)
            self._by_device[record.device_id].append(record)
            self._by_id[record.command_id] = record

    def get(self, command_id: str) -> CommandRecord | None:
        return self._by_id.get(command_id)

    def for_device(self, device_id: str) -> list[CommandRecord]:
        return list(self._by_device.get(device_id, []))

    def list(self) -> list[CommandRecord]:
        return list(self._all)

    def as_dicts(self, device_id: str | None = None) -> list[dict[str, Any]]:
        records = self.for_device(device_id) if device_id else self.list()
        return [r.to_dict() for r in records]

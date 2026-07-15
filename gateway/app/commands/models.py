"""Modelos semânticos do Universal Command Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class CommandName(StrEnum):
    """Comandos semânticos — a plataforma nunca monta bytes/raw strings."""

    SET_SERVER = "SET_SERVER"
    SET_APN = "SET_APN"
    REBOOT = "REBOOT"
    REQUEST_LOCATION = "REQUEST_LOCATION"
    REQUEST_STATUS = "REQUEST_STATUS"
    # Compat / aliases legados
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"
    SET_INTERVAL = "SET_INTERVAL"
    CONFIGURE = "CONFIGURE"


class CommandStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class CommandRequest:
    """Pedido semântico da plataforma."""

    name: CommandName | str
    parameters: dict[str, Any] = field(default_factory=dict)
    device_id: str | None = None
    protocol: str | None = None
    retry: int = 0
    timeout_s: float = 20.0

    def normalized_name(self) -> str:
        return str(self.name).upper()


@dataclass
class CommandRecord:
    command_id: str
    device_id: str
    name: str
    protocol: str
    parameters: dict[str, Any]
    status: CommandStatus
    payload_sent: bytes | None = None
    payload_received: bytes | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    sent_at: datetime | None = None
    finished_at: datetime | None = None
    attempts: int = 0
    max_retries: int = 0
    timeout_s: float = 20.0
    error: str | None = None
    result: str | None = None

    @staticmethod
    def new(
        *,
        device_id: str,
        name: str,
        protocol: str,
        parameters: dict[str, Any],
        max_retries: int = 0,
        timeout_s: float = 20.0,
    ) -> CommandRecord:
        return CommandRecord(
            command_id=str(uuid4()),
            device_id=device_id,
            name=name,
            protocol=protocol,
            parameters=dict(parameters),
            status=CommandStatus.PENDING,
            max_retries=max_retries,
            timeout_s=timeout_s,
        )

    @property
    def duration_ms(self) -> float | None:
        if self.finished_at is None:
            return None
        start = self.sent_at or self.created_at
        return round((self.finished_at - start).total_seconds() * 1000, 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "device_id": self.device_id,
            "name": self.name,
            "protocol": self.protocol,
            "parameters": self.parameters,
            "status": self.status.value,
            "payload_sent_hex": self.payload_sent.hex() if self.payload_sent else None,
            "payload_received_hex": self.payload_received.hex() if self.payload_received else None,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "timeout_s": self.timeout_s,
            "error": self.error,
            "result": self.result,
        }

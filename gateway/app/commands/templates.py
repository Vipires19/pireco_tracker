"""Templates de comando — semântica → payload por protocolo."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from app.commands.models import CommandName


Encoder = Callable[[dict[str, Any]], bytes]


class CommandTemplate(ABC):
    """Template independente do resto da plataforma."""

    name: str
    protocol: str
    default_retry: int = 0
    default_timeout_s: float = 20.0

    @abstractmethod
    def encode(self, parameters: dict[str, Any]) -> bytes:
        raise NotImplementedError

    def decode_ack(self, payload: bytes) -> bool:
        """Retorna True se o RX indicar ACK/sucesso para este comando."""
        text = payload.decode("utf-8", errors="ignore").upper()
        return any(token in text for token in ("OK", "SUCCEED", "SUCCESS", "ACK"))


class StringCommandTemplate(CommandTemplate):
    """Template baseado em string formatada (SMS/ASCII over TCP)."""

    def __init__(
        self,
        *,
        name: str,
        protocol: str,
        pattern: str,
        default_retry: int = 0,
        default_timeout_s: float = 20.0,
        encoding: str = "ascii",
    ) -> None:
        self.name = name
        self.protocol = protocol
        self.pattern = pattern
        self.default_retry = default_retry
        self.default_timeout_s = default_timeout_s
        self.encoding = encoding

    def encode(self, parameters: dict[str, Any]) -> bytes:
        try:
            rendered = self.pattern.format(**parameters)
        except KeyError as exc:
            raise ValueError(f"Parâmetro ausente para {self.name}: {exc}") from exc
        return rendered.encode(self.encoding)


def _require(params: dict[str, Any], *keys: str) -> None:
    missing = [k for k in keys if k not in params or params[k] in (None, "")]
    if missing:
        raise ValueError(f"Parâmetros obrigatórios ausentes: {', '.join(missing)}")


# --- GT06 Classic templates ---

GT06_CLASSIC_TEMPLATES: list[CommandTemplate] = [
    StringCommandTemplate(
        name=CommandName.SET_SERVER,
        protocol="gt06",
        pattern="SERVER,0,{host},{port},0#",
        default_retry=3,
        default_timeout_s=20.0,
    ),
    StringCommandTemplate(
        name=CommandName.SET_APN,
        protocol="gt06",
        pattern="APN,{apn}#",
        default_retry=2,
        default_timeout_s=20.0,
    ),
    StringCommandTemplate(
        name=CommandName.REBOOT,
        protocol="gt06",
        pattern="RESET#",
        default_retry=1,
        default_timeout_s=15.0,
    ),
    StringCommandTemplate(
        name=CommandName.REQUEST_LOCATION,
        protocol="gt06",
        pattern="WHERE#",
        default_retry=1,
        default_timeout_s=30.0,
    ),
    StringCommandTemplate(
        name=CommandName.REQUEST_STATUS,
        protocol="gt06",
        pattern="STATUS#",
        default_retry=1,
        default_timeout_s=20.0,
    ),
]

# --- GT06 V2 templates (textos diferentes, mesma semântica) ---

GT06_V2_TEMPLATES: list[CommandTemplate] = [
    StringCommandTemplate(
        name=CommandName.SET_SERVER,
        protocol="gt06_v2",
        pattern="SERVERIP,{host},{port}",
        default_retry=3,
        default_timeout_s=20.0,
    ),
    StringCommandTemplate(
        name=CommandName.SET_APN,
        protocol="gt06_v2",
        pattern="APN,{apn}",
        default_retry=2,
        default_timeout_s=20.0,
    ),
    StringCommandTemplate(
        name=CommandName.REBOOT,
        protocol="gt06_v2",
        pattern="REBOOT",
        default_retry=1,
        default_timeout_s=15.0,
    ),
    StringCommandTemplate(
        name=CommandName.REQUEST_LOCATION,
        protocol="gt06_v2",
        pattern="LJDW",
        default_retry=1,
        default_timeout_s=30.0,
    ),
    StringCommandTemplate(
        name=CommandName.REQUEST_STATUS,
        protocol="gt06_v2",
        pattern="CXZT",
        default_retry=1,
        default_timeout_s=20.0,
    ),
]


def build_default_templates() -> list[CommandTemplate]:
    return [*GT06_CLASSIC_TEMPLATES, *GT06_V2_TEMPLATES]


def normalize_set_server_params(parameters: dict[str, Any]) -> dict[str, Any]:
    """Aceita host/port ou aliases ip/port."""
    params = dict(parameters)
    if "host" not in params and "ip" in params:
        params["host"] = params["ip"]
    _require(params, "host", "port")
    params["port"] = int(params["port"])
    return params

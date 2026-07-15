"""Tipos de comando — enums legados + semânticos do Universal Command Engine."""

from enum import StrEnum

from app.commands.models import CommandName, CommandStatus


class CommandType(StrEnum):
    """Enum legado (minúsculo). Preferir CommandName para novos fluxos."""

    LOCK = "lock"
    UNLOCK = "unlock"
    REQUEST_LOCATION = "request_location"
    REBOOT = "reboot"
    CONFIGURE = "configure"
    SET_INTERVAL = "set_interval"
    SET_APN = "set_apn"
    SET_SERVER = "set_server"
    REQUEST_STATUS = "request_status"


__all__ = ["CommandName", "CommandStatus", "CommandType"]

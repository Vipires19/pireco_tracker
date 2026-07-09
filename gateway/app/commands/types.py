"""Estrutura preparada para comandos enviados aos rastreadores (sem implementação)."""

from enum import StrEnum


class CommandType(StrEnum):
    LOCK = "lock"
    UNLOCK = "unlock"
    REQUEST_LOCATION = "request_location"
    REBOOT = "reboot"
    CONFIGURE = "configure"
    SET_INTERVAL = "set_interval"
    SET_APN = "set_apn"

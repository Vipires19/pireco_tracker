"""Contrato base para montagem de comandos por protocolo."""

from abc import ABC, abstractmethod

from app.commands.types import CommandType


class CommandBuilder(ABC):
    @abstractmethod
    def supports(self, command_type: CommandType) -> bool:
        raise NotImplementedError

    @abstractmethod
    def build(self, command_type: CommandType, **params: object) -> bytes:
        raise NotImplementedError

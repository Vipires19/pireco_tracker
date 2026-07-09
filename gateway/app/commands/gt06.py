"""Implementação GT06 de CommandBuilder — estrutura preparada, sem comandos."""

from app.commands.builder import CommandBuilder
from app.commands.types import CommandType


class Gt06CommandBuilder(CommandBuilder):
    def supports(self, command_type: CommandType) -> bool:
        return command_type in CommandType

    def build(self, command_type: CommandType, **params: object) -> bytes:
        raise NotImplementedError(
            f"GT06 command '{command_type}' will be implemented in a future phase"
        )

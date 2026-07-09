"""Registro de builders de comando por protocolo."""

from app.commands.builder import CommandBuilder
from app.commands.types import CommandType


class CommandRegistry:
    def __init__(self) -> None:
        self._builders: list[CommandBuilder] = []

    def register(self, builder: CommandBuilder) -> None:
        self._builders.append(builder)

    def build(self, command_type: CommandType, **params: object) -> bytes:
        for builder in self._builders:
            if builder.supports(command_type):
                return builder.build(command_type, **params)
        raise NotImplementedError(
            f"Command '{command_type}' is not implemented for any registered protocol"
        )


command_registry = CommandRegistry()

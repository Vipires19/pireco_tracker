"""Command Registry — protocolos registram seus comandos semânticos."""

from __future__ import annotations

from app.commands.builder import CommandBuilder
from app.commands.models import CommandName
from app.commands.templates import (
    CommandTemplate,
    build_default_templates,
    normalize_set_server_params,
)
from app.commands.types import CommandType


class UniversalCommandRegistry:
    """Registro de templates por (protocol, command_name)."""

    def __init__(self) -> None:
        self._templates: dict[tuple[str, str], CommandTemplate] = {}
        self._legacy_builders: list[CommandBuilder] = []

    def register(self, template_or_builder: CommandTemplate | CommandBuilder) -> None:
        if isinstance(template_or_builder, CommandTemplate):
            key = (template_or_builder.protocol.lower(), template_or_builder.name.upper())
            self._templates[key] = template_or_builder
            return
        if isinstance(template_or_builder, CommandBuilder):
            self._legacy_builders.append(template_or_builder)
            return
        raise TypeError("Expected CommandTemplate or CommandBuilder")

    def register_command(self, protocol: str, template: CommandTemplate) -> None:
        template.protocol = protocol
        self.register(template)

    def get(self, protocol: str, command: str) -> CommandTemplate | None:
        return self._templates.get((protocol.lower(), command.upper()))

    def has(self, protocol: str, command: str) -> bool:
        return self.get(protocol, command) is not None

    def list_commands(self, protocol: str | None = None) -> list[CommandTemplate]:
        if protocol is None:
            return list(self._templates.values())
        proto = protocol.lower()
        return [t for (p, _), t in self._templates.items() if p == proto]

    def encode(self, protocol: str, command: str, parameters: dict) -> bytes:
        template = self.get(protocol, command)
        if template is None:
            raise KeyError(f"Comando '{command}' não registrado para protocolo '{protocol}'")
        params = dict(parameters)
        if command.upper() == CommandName.SET_SERVER:
            params = normalize_set_server_params(params)
        if command.upper() == CommandName.SET_APN and "apn" not in params:
            raise ValueError("Parâmetro obrigatório ausente: apn")
        return template.encode(params)

    def protocols(self) -> list[str]:
        return sorted({p for p, _ in self._templates.keys()})

    def build(self, command_type: CommandType | str, **params: object) -> bytes:
        """Compat com registry legado baseado em CommandBuilder."""
        for builder in self._legacy_builders:
            if builder.supports(CommandType(command_type)):  # type: ignore[arg-type]
                return builder.build(CommandType(command_type), **params)  # type: ignore[arg-type]
        raise NotImplementedError(
            f"Command '{command_type}' is not implemented for any registered protocol"
        )


# Alias histórico
CommandRegistry = UniversalCommandRegistry


def create_default_command_registry() -> UniversalCommandRegistry:
    registry = UniversalCommandRegistry()
    for template in build_default_templates():
        registry.register(template)
    return registry


command_registry = create_default_command_registry()

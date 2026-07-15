"""GT06 — registro de comandos no Universal Command Engine."""

from app.commands.builder import CommandBuilder
from app.commands.registry import UniversalCommandRegistry, command_registry
from app.commands.templates import GT06_CLASSIC_TEMPLATES, GT06_V2_TEMPLATES
from app.commands.types import CommandType


class Gt06CommandBuilder(CommandBuilder):
    """Builder legado — redireciona construção semântica via registry universal."""

    def supports(self, command_type: CommandType) -> bool:
        return command_type in CommandType

    def build(self, command_type: CommandType, **params: object) -> bytes:
        semantic = {
            CommandType.SET_SERVER: "SET_SERVER",
            CommandType.SET_APN: "SET_APN",
            CommandType.REBOOT: "REBOOT",
            CommandType.REQUEST_LOCATION: "REQUEST_LOCATION",
            CommandType.REQUEST_STATUS: "REQUEST_STATUS",
        }.get(command_type)
        if semantic is None:
            raise NotImplementedError(
                f"GT06 command '{command_type}' will be implemented in a future phase"
            )
        return command_registry.encode("gt06", semantic, dict(params))


def register_gt06_commands(registry: UniversalCommandRegistry | None = None) -> None:
    """GT06.register_command(...) — Classic + V2."""
    target = registry or command_registry
    for template in [*GT06_CLASSIC_TEMPLATES, *GT06_V2_TEMPLATES]:
        if not target.has(template.protocol, template.name):
            target.register_command(template.protocol, template)

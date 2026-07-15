"""Universal Command Engine — saída de comandos desacoplada de protocolos."""

from app.commands.dispatcher import CommandDispatcher
from app.commands.engine import CommandEngine, get_command_engine
from app.commands.gt06 import Gt06CommandBuilder, register_gt06_commands
from app.commands.history import CommandHistory
from app.commands.models import CommandName, CommandRecord, CommandRequest, CommandStatus
from app.commands.queue import CommandQueue
from app.commands.registry import command_registry
from app.commands.types import CommandType

# Garante templates GT06 no registry padrão (idempotente).
register_gt06_commands(command_registry)
# Mantém builder legado disponível para código antigo.
command_registry.register(Gt06CommandBuilder())

__all__ = [
    "CommandDispatcher",
    "CommandEngine",
    "CommandHistory",
    "CommandName",
    "CommandQueue",
    "CommandRecord",
    "CommandRequest",
    "CommandStatus",
    "CommandType",
    "Gt06CommandBuilder",
    "command_registry",
    "get_command_engine",
    "register_gt06_commands",
]

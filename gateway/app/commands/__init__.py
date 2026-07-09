from app.commands.gt06 import Gt06CommandBuilder
from app.commands.registry import command_registry
from app.commands.types import CommandType

command_registry.register(Gt06CommandBuilder())

__all__ = ["CommandType", "command_registry"]

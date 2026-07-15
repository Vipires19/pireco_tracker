"""Universal Command Engine — API única de envio de comandos."""

from __future__ import annotations

from typing import Any

from app.commands.dispatcher import CommandDispatcher, SessionManagerTransport, Transport
from app.commands.history import CommandHistory
from app.commands.models import CommandName, CommandRecord, CommandRequest, CommandStatus
from app.commands.queue import CommandQueue
from app.commands.registry import UniversalCommandRegistry, create_default_command_registry
from app.commands.response import ResponseHandler
from app.core.observability import get_logger

logger = get_logger(__name__)


class CommandEngine:
    """
    Interface única:

        await engine.send(device_id=..., command="SET_SERVER", parameters={...})

    A plataforma nunca monta bytes nem strings específicas de protocolo.
    """

    def __init__(
        self,
        *,
        registry: UniversalCommandRegistry | None = None,
        transport: Transport | None = None,
        default_protocol: str = "gt06",
    ) -> None:
        self.registry = registry or create_default_command_registry()
        self.queue = CommandQueue()
        self.history = CommandHistory()
        self._default_protocol = default_protocol

        if transport is None:
            from app.sessions.manager import session_manager

            transport = SessionManagerTransport(session_manager)

        self.response = ResponseHandler(self.registry, self.queue)
        self.dispatcher = CommandDispatcher(
            registry=self.registry,
            queue=self.queue,
            history=self.history,
            transport=transport,
            response_handler=self.response,
        )

    async def send(
        self,
        *,
        device_id: str,
        command: CommandName | str,
        parameters: dict[str, Any] | None = None,
        protocol: str | None = None,
        retry: int | None = None,
        timeout_s: float | None = None,
    ) -> CommandRecord:
        params = dict(parameters or {})
        name = str(command).upper()
        proto = (protocol or self._default_protocol).lower()

        template = self.registry.get(proto, name)
        if template is None:
            record = CommandRecord.new(
                device_id=device_id,
                name=name,
                protocol=proto,
                parameters=params,
            )
            record.status = CommandStatus.FAILED
            record.error = f"Comando '{name}' não registrado para protocolo '{proto}'"
            self.history.append(record)
            return record

        max_retries = template.default_retry if retry is None else retry
        timeout = template.default_timeout_s if timeout_s is None else timeout_s

        record = CommandRecord.new(
            device_id=device_id,
            name=name,
            protocol=proto,
            parameters=params,
            max_retries=max_retries,
            timeout_s=timeout,
        )
        logger.info(
            "CommandEngine.send device_id=%s command=%s protocol=%s",
            device_id,
            name,
            proto,
        )
        return await self.dispatcher.dispatch(record)

    async def send_request(self, request: CommandRequest) -> CommandRecord:
        if not request.device_id:
            raise ValueError("device_id é obrigatório")
        return await self.send(
            device_id=request.device_id,
            command=request.normalized_name(),
            parameters=request.parameters,
            protocol=request.protocol,
            retry=request.retry,
            timeout_s=request.timeout_s,
        )

    async def handle_rx(self, device_id: str, payload: bytes) -> CommandRecord | None:
        """Permite correlacionar RX sem acoplar o Gateway ao engine."""
        return await self.dispatcher.on_device_rx(device_id, payload)


_engine: CommandEngine | None = None


def get_command_engine() -> CommandEngine:
    global _engine
    if _engine is None:
        _engine = CommandEngine()
    return _engine

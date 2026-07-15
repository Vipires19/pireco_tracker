"""Dispatcher — localiza sessão, monta comando, envia e acompanha ciclo de vida."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Awaitable, Callable, Protocol

from app.commands.history import CommandHistory
from app.commands.models import CommandRecord, CommandStatus
from app.commands.queue import CommandQueue
from app.commands.registry import UniversalCommandRegistry
from app.commands.response import ResponseHandler
from app.core.observability import get_logger

logger = get_logger(__name__)


class Transport(Protocol):
    async def send(self, device_id: str, payload: bytes) -> bool: ...


class SessionManagerTransport:
    """Adapter sobre SessionManager.send_to_imei (sem alterar o manager)."""

    def __init__(self, session_manager) -> None:
        self._sessions = session_manager

    async def send(self, device_id: str, payload: bytes) -> bool:
        return await self._sessions.send_to_imei(device_id, payload)


class CommandDispatcher:
    def __init__(
        self,
        *,
        registry: UniversalCommandRegistry,
        queue: CommandQueue,
        history: CommandHistory,
        transport: Transport,
        response_handler: ResponseHandler | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._registry = registry
        self._queue = queue
        self._history = history
        self._transport = transport
        self._responses = response_handler or ResponseHandler(registry, queue)
        self._sleep = sleep or asyncio.sleep

    async def dispatch(self, record: CommandRecord) -> CommandRecord:
        """Envia um comando com retries/timeout e atualiza status."""
        self._history.append(record)
        await self._queue.enqueue(record)

        last_error: str | None = None
        max_attempts = max(1, record.max_retries + 1)

        for attempt in range(1, max_attempts + 1):
            record.attempts = attempt
            try:
                payload = self._registry.encode(record.protocol, record.name, record.parameters)
            except Exception as exc:
                record.status = CommandStatus.FAILED
                record.error = str(exc)
                record.finished_at = datetime.now(UTC)
                return record

            record.payload_sent = payload
            sent = await self._transport.send(record.device_id, payload)
            if not sent:
                last_error = "device offline or transport failed"
                record.status = CommandStatus.FAILED
                record.error = last_error
                if attempt < max_attempts:
                    await self._sleep(min(1.0 * attempt, 3.0))
                    continue
                record.finished_at = datetime.now(UTC)
                return record

            record.status = CommandStatus.SENT
            record.sent_at = datetime.now(UTC)
            record.error = None

            acknowledged = await self._wait_ack(record)
            if acknowledged:
                return record

            last_error = "timeout waiting for ack"
            record.status = CommandStatus.TIMEOUT
            record.error = last_error
            if attempt < max_attempts:
                logger.info(
                    "Command timeout, retrying command_id=%s attempt=%s/%s",
                    record.command_id,
                    attempt,
                    max_attempts,
                )
                continue

        record.finished_at = datetime.now(UTC)
        record.status = CommandStatus.TIMEOUT if last_error and "timeout" in last_error else CommandStatus.FAILED
        record.error = last_error
        return record

    async def _wait_ack(self, record: CommandRecord) -> bool:
        deadline = asyncio.get_event_loop().time() + record.timeout_s
        while asyncio.get_event_loop().time() < deadline:
            current = await self._queue.get(record.command_id)
            if current and current.status == CommandStatus.ACKNOWLEDGED:
                return True
            await self._sleep(0.05)
        return False

    async def on_device_rx(self, device_id: str, payload: bytes) -> CommandRecord | None:
        return await self._responses.handle_rx(device_id, payload)

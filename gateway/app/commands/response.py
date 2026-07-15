"""Response Handler — correlaciona RX com comandos enviados."""

from __future__ import annotations

from datetime import UTC, datetime

from app.commands.models import CommandRecord, CommandStatus
from app.commands.queue import CommandQueue
from app.commands.registry import UniversalCommandRegistry


class ResponseHandler:
    """
    Relaciona payload RX ao comando SENT mais recente do dispositivo.

    Correlation determinística por device_id + template.decode_ack.
    """

    def __init__(self, registry: UniversalCommandRegistry, queue: CommandQueue) -> None:
        self._registry = registry
        self._queue = queue

    async def handle_rx(self, device_id: str, payload: bytes) -> CommandRecord | None:
        inflight = await self._queue.list_inflight(device_id)
        candidates = [r for r in inflight if r.status == CommandStatus.SENT]
        if not candidates:
            return None

        # Mais recente enviado primeiro
        candidates.sort(key=lambda r: r.sent_at or r.created_at, reverse=True)
        for record in candidates:
            template = self._registry.get(record.protocol, record.name)
            matched = False
            if template is not None and template.decode_ack(payload):
                matched = True
            elif self._generic_ack(payload):
                matched = True

            if not matched:
                continue

            record.payload_received = payload
            record.status = CommandStatus.ACKNOWLEDGED
            record.finished_at = datetime.now(UTC)
            record.result = "ack"
            return record
        return None

    @staticmethod
    def _generic_ack(payload: bytes) -> bool:
        text = payload.decode("utf-8", errors="ignore").upper()
        return any(token in text for token in ("OK", "SUCCEED", "SUCCESS", "ACK"))

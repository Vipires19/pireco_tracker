"""Fila de comandos por dispositivo."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import Iterator

from app.commands.models import CommandRecord, CommandStatus


class CommandQueue:
    """Fila FIFO por device_id, com acesso por command_id."""

    def __init__(self) -> None:
        self._queues: dict[str, deque[CommandRecord]] = defaultdict(deque)
        self._by_id: dict[str, CommandRecord] = {}
        self._lock = asyncio.Lock()

    async def enqueue(self, record: CommandRecord) -> CommandRecord:
        async with self._lock:
            self._queues[record.device_id].append(record)
            self._by_id[record.command_id] = record
            return record

    async def peek(self, device_id: str) -> CommandRecord | None:
        async with self._lock:
            queue = self._queues.get(device_id)
            if not queue:
                return None
            return queue[0]

    async def pop_ready(self, device_id: str) -> CommandRecord | None:
        async with self._lock:
            queue = self._queues.get(device_id)
            if not queue:
                return None
            record = queue.popleft()
            return record

    async def get(self, command_id: str) -> CommandRecord | None:
        async with self._lock:
            return self._by_id.get(command_id)

    async def pending_for(self, device_id: str) -> list[CommandRecord]:
        async with self._lock:
            return [
                r
                for r in self._queues.get(device_id, [])
                if r.status in {CommandStatus.PENDING, CommandStatus.SENT}
            ]

    async def list_inflight(self, device_id: str | None = None) -> list[CommandRecord]:
        async with self._lock:
            records = list(self._by_id.values())
            if device_id is not None:
                records = [r for r in records if r.device_id == device_id]
            return [
                r
                for r in records
                if r.status in {CommandStatus.PENDING, CommandStatus.SENT}
            ]

    def __iter__(self) -> Iterator[CommandRecord]:
        return iter(self._by_id.values())

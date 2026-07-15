"""Testes do Universal Command Engine."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.commands.dispatcher import CommandDispatcher
from app.commands.engine import CommandEngine
from app.commands.history import CommandHistory
from app.commands.models import CommandName, CommandRecord, CommandStatus
from app.commands.queue import CommandQueue
from app.commands.registry import UniversalCommandRegistry, create_default_command_registry
from app.commands.response import ResponseHandler
from app.commands.templates import StringCommandTemplate


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bytes]] = []
        self.online = True

    async def send(self, device_id: str, payload: bytes) -> bool:
        if not self.online:
            return False
        self.sent.append((device_id, payload))
        return True


@pytest.fixture
def registry() -> UniversalCommandRegistry:
    return create_default_command_registry()


@pytest.mark.asyncio
async def test_command_registration(registry: UniversalCommandRegistry) -> None:
    assert registry.has("gt06", "SET_SERVER")
    assert registry.has("gt06_v2", "SET_SERVER")
    assert registry.has("gt06", CommandName.REBOOT)

    registry.register_command(
        "gt06",
        StringCommandTemplate(name="CUSTOM", protocol="gt06", pattern="X,{v}#"),
    )
    assert registry.encode("gt06", "CUSTOM", {"v": 1}) == b"X,1#"


@pytest.mark.asyncio
async def test_templates_are_protocol_specific(registry: UniversalCommandRegistry) -> None:
    classic = registry.encode("gt06", "SET_SERVER", {"host": "1.2.3.4", "port": 5023})
    v2 = registry.encode("gt06_v2", "SET_SERVER", {"host": "1.2.3.4", "port": 5023})
    assert classic == b"SERVER,0,1.2.3.4,5023,0#"
    assert v2 == b"SERVERIP,1.2.3.4,5023"
    assert classic != v2


@pytest.mark.asyncio
async def test_queue_fifo_and_lookup() -> None:
    queue = CommandQueue()
    a = CommandRecord.new(device_id="d1", name="REBOOT", protocol="gt06", parameters={})
    b = CommandRecord.new(device_id="d1", name="SET_APN", protocol="gt06", parameters={"apn": "x"})
    await queue.enqueue(a)
    await queue.enqueue(b)
    assert (await queue.peek("d1")).command_id == a.command_id
    popped = await queue.pop_ready("d1")
    assert popped.command_id == a.command_id
    assert (await queue.get(b.command_id)).name == "SET_APN"


@pytest.mark.asyncio
async def test_dispatcher_ack_correlation(registry: UniversalCommandRegistry) -> None:
    transport = FakeTransport()
    queue = CommandQueue()
    history = CommandHistory()
    dispatcher = CommandDispatcher(
        registry=registry,
        queue=queue,
        history=history,
        transport=transport,
        sleep=asyncio.sleep,
    )

    async def ack_later():
        await asyncio.sleep(0.05)
        await dispatcher.on_device_rx("imei-1", b"OK")

    task = asyncio.create_task(ack_later())
    record = CommandRecord.new(
        device_id="imei-1",
        name="REQUEST_STATUS",
        protocol="gt06",
        parameters={},
        max_retries=0,
        timeout_s=2.0,
    )
    result = await dispatcher.dispatch(record)
    await task

    assert result.status == CommandStatus.ACKNOWLEDGED
    assert result.payload_sent == b"STATUS#"
    assert result.payload_received == b"OK"
    assert transport.sent[0][1] == b"STATUS#"
    assert history.get(result.command_id) is not None


@pytest.mark.asyncio
async def test_timeout_and_retry(registry: UniversalCommandRegistry) -> None:
    transport = FakeTransport()

    async def fake_sleep(delay: float) -> None:
        return None

    dispatcher = CommandDispatcher(
        registry=registry,
        queue=CommandQueue(),
        history=CommandHistory(),
        transport=transport,
        sleep=fake_sleep,
    )
    record = CommandRecord.new(
        device_id="imei-2",
        name="REBOOT",
        protocol="gt06",
        parameters={},
        max_retries=2,
        timeout_s=0.01,
    )
    result = await dispatcher.dispatch(record)
    assert result.status == CommandStatus.TIMEOUT
    assert result.attempts == 3
    assert len(transport.sent) == 3


@pytest.mark.asyncio
async def test_transport_failure(registry: UniversalCommandRegistry) -> None:
    transport = FakeTransport()
    transport.online = False

    async def no_sleep(_: float) -> None:
        return None

    dispatcher = CommandDispatcher(
        registry=registry,
        queue=CommandQueue(),
        history=CommandHistory(),
        transport=transport,
        sleep=no_sleep,
    )
    record = CommandRecord.new(
        device_id="imei-3",
        name="REBOOT",
        protocol="gt06",
        parameters={},
        max_retries=1,
        timeout_s=0.01,
    )
    result = await dispatcher.dispatch(record)
    assert result.status == CommandStatus.FAILED
    assert "offline" in (result.error or "")


@pytest.mark.asyncio
async def test_engine_send_semantic_api(registry: UniversalCommandRegistry) -> None:
    transport = FakeTransport()
    engine = CommandEngine(registry=registry, transport=transport, default_protocol="gt06")

    async def ack():
        await asyncio.sleep(0.05)
        await engine.handle_rx("dev-9", b"OK")

    task = asyncio.create_task(ack())
    result = await engine.send(
        device_id="dev-9",
        command=CommandName.SET_SERVER,
        parameters={"host": "89.117.33.161", "port": 5023},
        retry=0,
        timeout_s=2.0,
    )
    await task

    assert result.status == CommandStatus.ACKNOWLEDGED
    assert result.payload_sent == b"SERVER,0,89.117.33.161,5023,0#"


@pytest.mark.asyncio
async def test_engine_v2_same_semantic_different_bytes(registry: UniversalCommandRegistry) -> None:
    transport = FakeTransport()
    engine = CommandEngine(registry=registry, transport=transport)

    async def ack():
        await asyncio.sleep(0.05)
        await engine.handle_rx("dev-v2", b"OK")

    task = asyncio.create_task(ack())
    result = await engine.send(
        device_id="dev-v2",
        command="SET_SERVER",
        parameters={"ip": "10.0.0.1", "port": 5023},
        protocol="gt06_v2",
        retry=0,
        timeout_s=2.0,
    )
    await task
    assert result.payload_sent == b"SERVERIP,10.0.0.1,5023"


@pytest.mark.asyncio
async def test_history_never_deletes(registry: UniversalCommandRegistry) -> None:
    transport = FakeTransport()
    history = CommandHistory()
    dispatcher = CommandDispatcher(
        registry=registry,
        queue=CommandQueue(),
        history=history,
        transport=transport,
        sleep=asyncio.sleep,
    )

    async def ack(device: str):
        await asyncio.sleep(0.02)
        await dispatcher.on_device_rx(device, b"OK")

    for i in range(3):
        device = f"d-{i}"
        task = asyncio.create_task(ack(device))
        await dispatcher.dispatch(
            CommandRecord.new(
                device_id=device,
                name="REQUEST_STATUS",
                protocol="gt06",
                parameters={},
                timeout_s=2.0,
            )
        )
        await task

    assert len(history.list()) == 3
    assert len(history.for_device("d-1")) == 1
    assert all(item["status"] == "ACKNOWLEDGED" for item in history.as_dicts())


@pytest.mark.asyncio
async def test_response_handler_ignores_unrelated_rx(registry: UniversalCommandRegistry) -> None:
    queue = CommandQueue()
    handler = ResponseHandler(registry, queue)
    record = CommandRecord.new(device_id="x", name="REBOOT", protocol="gt06", parameters={})
    record.status = CommandStatus.SENT
    record.sent_at = datetime.now(UTC)
    await queue.enqueue(record)

    matched = await handler.handle_rx("x", b"NOPE")
    assert matched is None
    assert record.status == CommandStatus.SENT

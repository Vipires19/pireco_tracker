"""Servidor TCP genérico — detecta protocolo via Registry e delega o handling."""

from __future__ import annotations

import asyncio
import uuid
from asyncio import StreamReader, StreamWriter

from app.config import get_settings
from app.contracts.messages import DeviceConnection
from app.core.observability import bind_context, get_logger, log_with_fields, new_trace_id
from app.exceptions import ConnectionTimeoutError, PublishEventError
from app.observability.metrics import (
    BYTES_RECEIVED,
    TCP_CONNECTIONS_ACTIVE,
    TCP_CONNECTIONS_CLOSED,
)
from app.observability.session_lifecycle import (
    CLOSE_CLIENT,
    CLOSE_SERVER,
    CLOSE_TIMEOUT,
    SessionLifecycle,
)
from app.protocols import ProtocolDetector, create_default_registry
from app.protocols.detector import MIN_DETECT_BYTES
from app.protocols.registry import UNKNOWN_PROTOCOL_NAME
from app.publisher.redis_publisher import event_publisher
from app.sessions.manager import session_manager

logger = get_logger(__name__)


class GatewayTcpServer:
    """TCP gateway multi-protocolo. Não conhece implementações concretas (ex.: GT06)."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._connection_semaphore = asyncio.Semaphore(self._settings.max_connections)
        self._server: asyncio.Server | None = None
        self._registry = create_default_registry()
        self._detector = ProtocolDetector(self._registry)

    @property
    def active_connections(self) -> int:
        return session_manager.active_count

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            host=self._settings.tcp_host,
            port=self._settings.tcp_port,
            reuse_address=True,
            start_serving=True,
        )
        addr = self._server.sockets[0].getsockname() if self._server.sockets else ("?", "?")
        log_with_fields(
            logger,
            20,
            "TCP gateway listening",
            host=addr[0],
            port=addr[1],
            protocols=self._registry.names(),
        )

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        acquired = False
        try:
            await asyncio.wait_for(self._connection_semaphore.acquire(), timeout=1.0)
            acquired = True
        except TimeoutError:
            peer = writer.get_extra_info("peername")
            log_with_fields(logger, 30, "Connection rejected", reason="max_connections", peer=str(peer))
            writer.close()
            await writer.wait_closed()
            return

        connection_id = str(uuid.uuid4())
        peer = writer.get_extra_info("peername")
        if peer:
            remote_host = str(peer[0])
            remote_port = int(peer[1]) if len(peer) > 1 else 0
            peer_str = f"{remote_host}:{remote_port}"
        else:
            remote_host = "unknown"
            remote_port = 0
            peer_str = "unknown"

        lifecycle = SessionLifecycle(session_id=connection_id, remote_ip=peer_str)

        bind_context(connection_id=connection_id, remote_ip=peer_str)
        await session_manager.register(connection_id, peer_str, writer)
        TCP_CONNECTIONS_ACTIVE.set(session_manager.active_count)
        lifecycle.on_connect(session_manager.active_count)
        log_with_fields(
            logger,
            20,
            "Connection accepted",
            remote_ip=peer_str,
            connection_id=connection_id,
        )

        try:
            protocol, initial_buffer = await self._detect_protocol(
                reader,
                lifecycle,
                connection_id=connection_id,
                remote_ip=peer_str,
            )
            if protocol is None:
                return

            if protocol.name == UNKNOWN_PROTOCOL_NAME:
                log_with_fields(
                    logger,
                    20,
                    "Entering Learning Mode",
                    session_id=connection_id,
                    remote_ip=remote_host,
                    remote_port=remote_port,
                )

            await protocol.handle_connection(
                reader,
                writer,
                connection_id=connection_id,
                remote_ip=peer_str,
                lifecycle=lifecycle,
                initial_buffer=initial_buffer,
                remote_port=remote_port,
            )
        finally:
            removed = await session_manager.remove(connection_id)
            TCP_CONNECTIONS_CLOSED.inc()
            TCP_CONNECTIONS_ACTIVE.set(session_manager.active_count)
            lifecycle.on_close(session_manager.active_count)

            if removed and removed.imei:
                disconnect = DeviceConnection(
                    schema_version=1,
                    trace_id=new_trace_id(),
                    tracker_imei=removed.imei,
                    action="disconnect",
                    received_at=removed.last_activity,
                    connection_id=connection_id,
                    remote_ip=peer_str,
                )
                try:
                    await event_publisher.publish(disconnect)
                except PublishEventError:
                    log_with_fields(logger, 40, "Failed to publish disconnect event")

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

            if acquired:
                self._connection_semaphore.release()

    async def _detect_protocol(
        self,
        reader: StreamReader,
        lifecycle: SessionLifecycle,
        *,
        connection_id: str,
        remote_ip: str,
    ):
        """Lê bytes iniciais até Fingerprint + Registry selecionarem o protocolo."""
        buffer = bytearray()

        while True:
            try:
                data = await asyncio.wait_for(
                    reader.read(self._settings.read_buffer_size),
                    timeout=self._settings.connection_idle_timeout,
                )
            except TimeoutError:
                timeout_exc = ConnectionTimeoutError(
                    f"Idle timeout connection_id={connection_id}"
                )
                lifecycle.set_close_reason(CLOSE_TIMEOUT)
                lifecycle.on_exception(timeout_exc, close_reason=CLOSE_TIMEOUT)
                log_with_fields(
                    logger,
                    30,
                    "Tracker error on connection",
                    error=str(timeout_exc),
                    hex=buffer.hex() if buffer else None,
                    remote_ip=remote_ip,
                    connection_id=connection_id,
                )
                return None, buffer

            if not data:
                lifecycle.set_close_reason(CLOSE_CLIENT)
                if not buffer:
                    log_with_fields(
                        logger,
                        30,
                        "Client closed connection before sending data.",
                        remote_ip=remote_ip,
                        connection_id=connection_id,
                    )
                return None, buffer

            last_rx_hex = data.hex()
            lifecycle.on_rx(data)
            log_with_fields(
                logger,
                20,
                f"Bytes recebidos: {len(data)}",
                bytes_received=len(data),
                hex=last_rx_hex,
                remote_ip=remote_ip,
                connection_id=connection_id,
            )
            BYTES_RECEIVED.inc(len(data))
            buffer.extend(data)

            protocol = self._detector.detect(bytes(buffer))
            if protocol is not None:
                log_with_fields(
                    logger,
                    20,
                    "Protocol resolved",
                    protocol=protocol.name,
                    connection_id=connection_id,
                    remote_ip=remote_ip,
                    learning_mode=protocol.name == UNKNOWN_PROTOCOL_NAME,
                )
                return protocol, buffer

            if len(buffer) >= MIN_DETECT_BYTES:
                # Sem Unknown registrado — não deve ocorrer no bootstrap padrão.
                lifecycle.set_close_reason(CLOSE_SERVER)
                log_with_fields(
                    logger,
                    30,
                    "No protocol matched and Learning Mode unavailable",
                    connection_id=connection_id,
                    remote_ip=remote_ip,
                    hex=buffer.hex(),
                    bytes=len(buffer),
                )
                return None, buffer


# Compatibilidade com bootstrap legado
GT06TcpServer = GatewayTcpServer

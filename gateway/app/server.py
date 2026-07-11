import asyncio
import uuid
from asyncio import StreamReader, StreamWriter

from app.contracts.messages import DeviceConnection, DeviceHeartbeat
from app.exceptions import (
    CRCValidationError,
    ConnectionTimeoutError,
    InvalidPacketError,
    PublishEventError,
    TrackerError,
)
from app.core.observability import bind_context, get_logger, log_with_fields, new_trace_id

from app.config import get_settings
from app.domain.mapper import gt06_domain_mapper
from app.observability.metrics import (
    ACKS_SENT,
    BYTES_RECEIVED,
    BYTES_SENT,
    PACKETS_INVALID,
    PACKETS_RECEIVED,
    TCP_CONNECTIONS_ACTIVE,
    TCP_CONNECTIONS_CLOSED,
)
from app.protocol import build_ack, extract_packets, parse_packet
from app.protocol.parser import _parse_packet_or_raise
from app.publisher.redis_publisher import event_publisher
from app.sessions.manager import session_manager

logger = get_logger(__name__)


def _discard_reason(frame: bytes) -> str:
    """Classifica o motivo do descarte sem alterar o parser público."""
    try:
        _parse_packet_or_raise(frame)
    except CRCValidationError:
        return "CRC inválido"
    except InvalidPacketError as exc:
        msg = str(exc)
        if msg == "Invalid start bytes":
            return "Cabeçalho desconhecido"
        return "Tamanho inválido"
    except Exception as exc:
        return f"exceção inesperada: {exc}"
    return "desconhecido"


class GT06TcpServer:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._connection_semaphore = asyncio.Semaphore(self._settings.max_connections)
        self._server: asyncio.Server | None = None

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
        log_with_fields(logger, 20, "GT06 TCP server listening", host=addr[0], port=addr[1])

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
        peer_str = f"{peer[0]}:{peer[1]}" if peer else "unknown"
        buffer = bytearray()
        received_any_data = False
        last_rx_hex: str | None = None

        bind_context(connection_id=connection_id, remote_ip=peer_str)
        await session_manager.register(connection_id, peer_str, writer)
        TCP_CONNECTIONS_ACTIVE.set(session_manager.active_count)
        log_with_fields(
            logger,
            20,
            "Connection accepted",
            remote_ip=peer_str,
            connection_id=connection_id,
        )

        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        reader.read(self._settings.read_buffer_size),
                        timeout=self._settings.connection_idle_timeout,
                    )
                except TimeoutError as exc:
                    raise ConnectionTimeoutError(
                        f"Idle timeout connection_id={connection_id}"
                    ) from exc

                if not data:
                    if not received_any_data:
                        log_with_fields(
                            logger,
                            30,
                            "Client closed connection before sending data.",
                            remote_ip=peer_str,
                            connection_id=connection_id,
                        )
                    break

                received_any_data = True
                last_rx_hex = data.hex()
                log_with_fields(
                    logger,
                    20,
                    f"Bytes recebidos: {len(data)}",
                    bytes_received=len(data),
                    hex=last_rx_hex,
                    remote_ip=peer_str,
                    connection_id=connection_id,
                )

                BYTES_RECEIVED.inc(len(data))
                buffer.extend(data)
                frames, buffer = extract_packets(buffer)

                for frame in frames:
                    PACKETS_RECEIVED.inc()
                    frame_hex = frame.hex()

                    try:
                        packet = parse_packet(frame)
                    except Exception:
                        PACKETS_INVALID.inc()
                        logger.exception("Parser exception")
                        log_with_fields(
                            logger,
                            40,
                            "Parser exception",
                            hex=frame_hex,
                            remote_ip=peer_str,
                            connection_id=connection_id,
                        )
                        continue

                    if packet is None:
                        PACKETS_INVALID.inc()
                        reason = _discard_reason(frame)
                        log_with_fields(
                            logger,
                            30,
                            reason,
                            hex=frame_hex,
                            remote_ip=peer_str,
                            connection_id=connection_id,
                        )
                        continue

                    trace_id = new_trace_id()
                    bind_context(
                        trace_id=trace_id,
                        packet_type=f"0x{packet.protocol_number:02X}",
                    )

                    if packet.imei:
                        await session_manager.bind_imei(connection_id, packet.imei)
                        bind_context(imei=packet.imei)

                    current = await session_manager.get_by_connection(connection_id)
                    tracker_imei = packet.imei or (current.imei if current else None)

                    domain_message = gt06_domain_mapper.map_packet(
                        packet,
                        tracker_imei=tracker_imei,
                        connection_id=connection_id,
                        remote_ip=peer_str,
                        trace_id=trace_id,
                    )

                    if domain_message is not None:
                        bind_context(event_type=domain_message.message_type.value)
                        await event_publisher.publish(domain_message)

                        if isinstance(domain_message, DeviceHeartbeat):
                            await session_manager.record_heartbeat(connection_id)
                        else:
                            await session_manager.touch(connection_id)

                    ack = build_ack(packet.protocol_number, packet.serial_number)
                    writer.write(ack)
                    await writer.drain()
                    BYTES_SENT.inc(len(ack))
                    ACKS_SENT.inc()

        except TrackerError as exc:
            log_with_fields(
                logger,
                30,
                "Tracker error on connection",
                error=str(exc),
                hex=last_rx_hex,
                remote_ip=peer_str,
                connection_id=connection_id,
            )
        except Exception:
            logger.exception("Unexpected connection error")
            log_with_fields(
                logger,
                40,
                "Unexpected connection error details",
                hex=last_rx_hex,
                remote_ip=peer_str,
                connection_id=connection_id,
            )
        finally:
            removed = await session_manager.remove(connection_id)
            TCP_CONNECTIONS_CLOSED.inc()
            TCP_CONNECTIONS_ACTIVE.set(session_manager.active_count)

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

"""BaseGT06Protocol — lógica comum da família GT06 (Classic / V2 / futuras)."""

from __future__ import annotations

import asyncio
from abc import ABC
from asyncio import StreamReader, StreamWriter
from typing import Any, ClassVar

from app.config import get_settings
from app.contracts.messages import DeviceHeartbeat
from app.core.observability import bind_context, get_logger, log_with_fields, new_trace_id
from app.domain.mapper import gt06_domain_mapper
from app.exceptions import (
    CRCValidationError,
    ConnectionTimeoutError,
    InvalidPacketError,
    TrackerError,
)
from app.observability.metrics import (
    ACKS_SENT,
    BYTES_RECEIVED,
    BYTES_SENT,
    PACKETS_INVALID,
    PACKETS_RECEIVED,
)
from app.observability.session_lifecycle import (
    CLOSE_CLIENT,
    CLOSE_EXCEPTION,
    CLOSE_SOCKET,
    CLOSE_TIMEOUT,
    SessionLifecycle,
)
from app.protocols.base import BaseProtocol
from app.protocols.gt06.codec import Gt06Codec, extract_frames
from app.protocols.gt06.decoder import PacketDecoder
from app.protocols.gt06.packets import Packet, ProtocolNumber
from app.publisher.redis_publisher import event_publisher
from app.sessions.manager import session_manager

logger = get_logger(__name__)


def _is_socket_error(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return False
    return isinstance(
        exc,
        (
            ConnectionResetError,
            ConnectionAbortedError,
            BrokenPipeError,
            ConnectionRefusedError,
            OSError,
        ),
    )


class BaseGT06Protocol(BaseProtocol, ABC):
    """
    Concentra: extração de frames, CRC, header/rodapé, ACK, login, heartbeat,
    GPS e o loop TCP. Variantes só diferem em SIGNATURES / start_marker / name.
    """

    SIGNATURES: ClassVar[tuple[bytes, ...]] = ()
    SIGNATURE_REASON: ClassVar[str] = ""
    START_MARKER: ClassVar[bytes] = b""

    def __init__(self) -> None:
        if not self.START_MARKER:
            raise ValueError(f"{type(self).__name__} must define START_MARKER")
        self._codec = Gt06Codec(protocol_name=self.name, start_marker=self.START_MARKER)
        self._decoder = PacketDecoder(protocol_name=self.name, start_marker=self.START_MARKER)

    @property
    def codec(self) -> Gt06Codec:
        return self._codec

    @property
    def decoder(self) -> PacketDecoder:
        return self._decoder

    @property
    def has_parser(self) -> bool:
        return True

    def match(self, data: bytes) -> bool:
        if len(data) < 2 or not self.SIGNATURES:
            return False
        return any(data.startswith(sig) for sig in self.SIGNATURES)

    def parse_packet(self, raw: bytes) -> Packet | None:
        return self._decoder.decode(raw)

    def parse_packet_or_raise(self, raw: bytes) -> Packet:
        return self._decoder.decode_or_raise(raw)

    def build_ack(self, protocol_number: int, serial_number: int) -> bytes:  # type: ignore[override]
        return self._codec.encode_ack(protocol_number, serial_number)

    def extract_packets(self, buffer: bytearray) -> tuple[list[bytes], bytearray]:
        return extract_frames(buffer, start_markers=(self.START_MARKER,))

    def discard_reason(self, frame: bytes) -> str:
        try:
            self.parse_packet_or_raise(frame)
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

    def is_login(self, packet: Packet) -> bool:
        return packet.protocol_number == ProtocolNumber.LOGIN

    def is_heartbeat(self, packet: Packet) -> bool:
        return packet.protocol_number == ProtocolNumber.HEARTBEAT

    def is_gps(self, packet: Packet) -> bool:
        return packet.protocol_number in (
            ProtocolNumber.GPS_LOCATION,
            ProtocolNumber.GPS_LOCATION_4G,
        )

    async def handle_connection(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        *,
        connection_id: str,
        remote_ip: str,
        lifecycle: Any,
        initial_buffer: bytes | bytearray,
        remote_port: int = 0,
    ) -> None:
        settings = get_settings()
        session: SessionLifecycle = lifecycle
        buffer = bytearray(initial_buffer)
        received_any_data = len(buffer) > 0
        last_rx_hex: str | None = buffer.hex() if buffer else None
        session.protocol = self.name

        try:
            if buffer:
                await self._process_buffer(
                    buffer,
                    writer,
                    connection_id=connection_id,
                    remote_ip=remote_ip,
                    lifecycle=session,
                )

            while True:
                try:
                    data = await asyncio.wait_for(
                        reader.read(settings.read_buffer_size),
                        timeout=settings.connection_idle_timeout,
                    )
                except TimeoutError as exc:
                    raise ConnectionTimeoutError(
                        f"Idle timeout connection_id={connection_id}"
                    ) from exc

                if not data:
                    session.set_close_reason(CLOSE_CLIENT)
                    if not received_any_data:
                        log_with_fields(
                            logger,
                            30,
                            "Client closed connection before sending data.",
                            remote_ip=remote_ip,
                            connection_id=connection_id,
                        )
                    break

                received_any_data = True
                last_rx_hex = data.hex()
                session.on_rx(data)
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
                await self._process_buffer(
                    buffer,
                    writer,
                    connection_id=connection_id,
                    remote_ip=remote_ip,
                    lifecycle=session,
                )

        except ConnectionTimeoutError as exc:
            session.set_close_reason(CLOSE_TIMEOUT)
            session.on_exception(exc, close_reason=CLOSE_TIMEOUT)
            log_with_fields(
                logger,
                30,
                "Tracker error on connection",
                error=str(exc),
                hex=last_rx_hex,
                remote_ip=remote_ip,
                connection_id=connection_id,
            )
        except TrackerError as exc:
            reason = CLOSE_SOCKET if _is_socket_error(exc) else CLOSE_EXCEPTION
            session.set_close_reason(reason)
            session.on_exception(exc, close_reason=reason)
            log_with_fields(
                logger,
                30,
                "Tracker error on connection",
                error=str(exc),
                hex=last_rx_hex,
                remote_ip=remote_ip,
                connection_id=connection_id,
            )
        except Exception as exc:
            reason = CLOSE_SOCKET if _is_socket_error(exc) else CLOSE_EXCEPTION
            session.set_close_reason(reason)
            session.on_exception(exc, close_reason=reason)
            logger.exception("Unexpected connection error")
            log_with_fields(
                logger,
                40,
                "Unexpected connection error details",
                hex=last_rx_hex,
                remote_ip=remote_ip,
                connection_id=connection_id,
            )

    async def _process_buffer(
        self,
        buffer: bytearray,
        writer: StreamWriter,
        *,
        connection_id: str,
        remote_ip: str,
        lifecycle: SessionLifecycle,
    ) -> None:
        frames, remaining = self.extract_packets(buffer)
        buffer.clear()
        buffer.extend(remaining)

        for frame in frames:
            PACKETS_RECEIVED.inc()
            frame_hex = frame.hex()

            try:
                packet = self.parse_packet(frame)
            except Exception as exc:
                PACKETS_INVALID.inc()
                lifecycle.on_parser(frame, success=False)
                lifecycle.on_exception(exc, affects_close=False)
                logger.exception("Parser exception")
                log_with_fields(
                    logger,
                    40,
                    "Parser exception",
                    hex=frame_hex,
                    remote_ip=remote_ip,
                    connection_id=connection_id,
                )
                continue

            if packet is None:
                PACKETS_INVALID.inc()
                lifecycle.on_parser(frame, success=False)
                reason = self.discard_reason(frame)
                log_with_fields(
                    logger,
                    30,
                    reason,
                    hex=frame_hex,
                    remote_ip=remote_ip,
                    connection_id=connection_id,
                )
                continue

            lifecycle.on_parser(
                frame,
                success=True,
                protocol_number=packet.protocol_number,
            )
            lifecycle.on_packet_type(packet.protocol_number)

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
                remote_ip=remote_ip,
                trace_id=trace_id,
            )

            if domain_message is not None:
                bind_context(event_type=domain_message.message_type.value)
                await event_publisher.publish(domain_message)

                if isinstance(domain_message, DeviceHeartbeat):
                    await session_manager.record_heartbeat(connection_id)
                else:
                    await session_manager.touch(connection_id)

            ack = self.build_ack(packet.protocol_number, packet.serial_number)
            writer.write(ack)
            await writer.drain()
            BYTES_SENT.inc(len(ack))
            ACKS_SENT.inc()
            lifecycle.on_ack_sent(ack)

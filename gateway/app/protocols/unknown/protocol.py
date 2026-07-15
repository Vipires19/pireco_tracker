"""UnknownProtocol — Learning Mode (captura sem interpretação)."""

from __future__ import annotations

import asyncio
import logging
import traceback
from asyncio import StreamReader, StreamWriter
from typing import Any, ClassVar

from app.config import get_settings
from app.core.observability import get_logger, log_with_fields
from app.exceptions import ConnectionTimeoutError
from app.learning.session_recorder import SessionRecorder
from app.learning.session_store import get_session_store
from app.observability.metrics import BYTES_RECEIVED
from app.observability.session_lifecycle import (
    CLOSE_CLIENT,
    CLOSE_EXCEPTION,
    CLOSE_SOCKET,
    CLOSE_TIMEOUT,
    SessionLifecycle,
)
from app.protocols.base import BaseProtocol

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


def _split_peer(remote_ip: str, remote_port: int) -> tuple[str, int]:
    """Extrai host/porta a partir do peer legado \"ip:port\" quando necessário."""
    if remote_port:
        if remote_ip.count(":") == 1:
            host, _, _port = remote_ip.partition(":")
            return host, remote_port
        return remote_ip, remote_port
    if remote_ip.count(":") == 1:
        host, _, port_s = remote_ip.partition(":")
        try:
            return host, int(port_s)
        except ValueError:
            return remote_ip, 0
    return remote_ip, 0


class UnknownProtocol(BaseProtocol):
    """
    Fallback de Learning Mode.

    Nunca interpreta pacotes nem publica eventos de domínio.
    Apenas mantém a sessão aberta e grava RX/TX para análise.
    """

    SIGNATURES: ClassVar[tuple[bytes, ...]] = ()
    SIGNATURE_REASON: ClassVar[str] = ""

    @property
    def name(self) -> str:
        return "unknown"

    @property
    def has_parser(self) -> bool:
        return False

    def match(self, data: bytes) -> bool:
        # Nunca reivindica a conexão via match — só entra como fallback do detector.
        return False

    def parse_packet(self, raw: bytes) -> None:
        return None

    def build_ack(self, *args: Any, **kwargs: Any) -> bytes:
        return b""

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
        session.protocol = self.name

        host, port = _split_peer(remote_ip, remote_port)

        recorder = SessionRecorder(
            session_id=connection_id,
            remote_ip=host,
            remote_port=port,
            connected_at=session.connected_at,
        )
        recorder.record_connect()

        if initial_buffer:
            recorder.record_rx(bytes(initial_buffer), elapsed_ms=session.elapsed_ms)

        log_with_fields(
            logger,
            logging.INFO,
            "Learning Mode started",
            session_id=connection_id,
            remote_ip=host,
            remote_port=port,
            protocol="unknown",
            bytes=len(initial_buffer),
        )

        try:
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
                    break

                session.on_rx(data)
                recorder.record_rx(data)
                BYTES_RECEIVED.inc(len(data))

                rx_fields: dict[str, Any] = {
                    "bytes_received": len(data),
                    "remote_ip": remote_ip,
                    "connection_id": connection_id,
                    "learning_mode": True,
                }
                if logger.isEnabledFor(logging.INFO):
                    rx_fields["hex"] = data.hex()
                log_with_fields(
                    logger,
                    logging.INFO,
                    f"Bytes recebidos: {len(data)}",
                    **rx_fields,
                )

        except ConnectionTimeoutError as exc:
            session.set_close_reason(CLOSE_TIMEOUT)
            recorder.record_timeout(message=str(exc))
            log_with_fields(
                logger,
                logging.WARNING,
                "Learning Mode timeout",
                error=str(exc),
                session_id=connection_id,
                remote_ip=remote_ip,
            )
        except Exception as exc:
            reason = CLOSE_SOCKET if _is_socket_error(exc) else CLOSE_EXCEPTION
            session.set_close_reason(reason)
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            recorder.record_exception(exc, traceback_text=tb)
            session.on_exception(exc, close_reason=reason)
            logger.exception("Learning Mode unexpected error")
        finally:
            reason = session.close_reason or CLOSE_CLIENT
            payload = recorder.finish(reason)
            try:
                get_session_store().append(payload)
            except Exception:
                logger.exception(
                    "Failed to persist learning session session_id=%s",
                    connection_id,
                )

"""Ciclo de vida e logs estruturados de sessão TCP do Gateway."""

from __future__ import annotations

import logging
import time
import traceback
from datetime import UTC, datetime
from typing import Any

from app.core.observability import get_logger, log_with_fields
from app.observability.formatting import bytes_to_ascii, bytes_to_hex
from app.observability.metrics import (
    CONNECTIONS_ACTIVE,
    CONNECTIONS_TOTAL,
    EXCEPTIONS_TOTAL,
    RX_BYTES_TOTAL,
    SESSIONS_CLOSED_TOTAL,
    TCP_CONNECTIONS_ACTIVE,
    TX_BYTES_TOTAL,
)
from app.protocol.constants import ProtocolNumber

logger = get_logger(__name__)

CLOSE_CLIENT = "client_closed"
CLOSE_SERVER = "server_closed"
CLOSE_TIMEOUT = "timeout"
CLOSE_PARSER = "parser_error"
CLOSE_SOCKET = "socket_error"
CLOSE_EXCEPTION = "exception"

_PACKET_EVENTS: dict[int, str] = {
    ProtocolNumber.LOGIN: "LOGIN_PACKET",
    ProtocolNumber.GPS_LOCATION: "GPS_PACKET",
    ProtocolNumber.GPS_LOCATION_4G: "GPS_PACKET",
    ProtocolNumber.HEARTBEAT: "HEARTBEAT",
}


class SessionLifecycle:
    """Rastreia métricas e emite eventos estruturados de uma conexão TCP."""

    def __init__(self, session_id: str, remote_ip: str) -> None:
        self.session_id = session_id
        self.remote_ip = remote_ip
        self.protocol: str | None = None
        self._connected_mono = time.monotonic()
        self._connected_at = datetime.now(UTC)
        self._first_byte_mono: float | None = None
        self.bytes_rx = 0
        self.bytes_tx = 0
        self.reads = 0
        self.writes = 0
        self.last_rx: bytes | None = None
        self.last_tx: bytes | None = None
        self.close_reason: str | None = None
        self._closed = False

    @property
    def connected_at(self) -> datetime:
        return self._connected_at

    @property
    def elapsed_ms(self) -> float:
        return round((time.monotonic() - self._connected_mono) * 1000, 3)

    @property
    def time_to_first_byte_ms(self) -> float | None:
        if self._first_byte_mono is None:
            return None
        return round((self._first_byte_mono - self._connected_mono) * 1000, 3)

    def _base_fields(self, **extra: Any) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "event": extra.pop("event"),
            "session_id": self.session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "remote_ip": self.remote_ip,
        }
        if self.protocol is not None:
            fields["protocol"] = self.protocol
        fields.update(extra)
        return fields

    def _emit(self, level: int, message: str, **fields: Any) -> None:
        if not logger.isEnabledFor(level):
            return
        log_with_fields(logger, level, message, **self._base_fields(**fields))

    def _payload_fields(self, data: bytes) -> dict[str, Any]:
        """Converte HEX/ASCII apenas se o nível de log estiver habilitado."""
        if not logger.isEnabledFor(logging.INFO):
            return {"bytes": len(data)}
        return {
            "bytes": len(data),
            "hex": bytes_to_hex(data),
            "ascii": bytes_to_ascii(data),
        }

    def on_connect(self, active_count: int) -> None:
        CONNECTIONS_TOTAL.inc()
        CONNECTIONS_ACTIVE.set(active_count)
        TCP_CONNECTIONS_ACTIVE.set(active_count)
        self._emit(
            logging.INFO,
            "CONNECT",
            event="CONNECT",
            elapsed_ms=0.0,
        )

    def on_first_byte(self) -> None:
        if self._first_byte_mono is not None:
            return
        self._first_byte_mono = time.monotonic()
        self._emit(
            logging.INFO,
            "FIRST_BYTE",
            event="FIRST_BYTE",
            duration_ms=self.time_to_first_byte_ms,
            elapsed_ms=self.elapsed_ms,
        )

    def on_rx(self, data: bytes) -> None:
        self.reads += 1
        self.bytes_rx += len(data)
        self.last_rx = data
        RX_BYTES_TOTAL.inc(len(data))
        if self._first_byte_mono is None:
            self.on_first_byte()
        fields = self._payload_fields(data)
        fields.update(event="RX", elapsed_ms=self.elapsed_ms)
        self._emit(logging.INFO, "RX", **fields)

    def on_tx(self, data: bytes) -> None:
        self.writes += 1
        self.bytes_tx += len(data)
        self.last_tx = data
        TX_BYTES_TOTAL.inc(len(data))
        fields = self._payload_fields(data)
        fields.update(event="TX", elapsed_ms=self.elapsed_ms)
        self._emit(logging.INFO, "TX", **fields)

    def on_parser(self, frame: bytes, *, success: bool, protocol_number: int | None = None) -> None:
        if protocol_number is not None:
            self.protocol = self.protocol or "gt06"
        fields: dict[str, Any] = {
            "event": "PARSER",
            "elapsed_ms": self.elapsed_ms,
            "success": success,
            "bytes": len(frame),
        }
        if protocol_number is not None:
            fields["protocol_number"] = f"0x{protocol_number:02X}"
        if logger.isEnabledFor(logging.INFO):
            fields["hex"] = bytes_to_hex(frame)
            fields["ascii"] = bytes_to_ascii(frame)
        self._emit(logging.INFO, "PARSER", **fields)

    def on_packet_type(self, protocol_number: int) -> None:
        event = _PACKET_EVENTS.get(protocol_number)
        if event is None:
            return
        self.protocol = self.protocol or "gt06"
        self._emit(
            logging.INFO,
            event,
            event=event,
            protocol_number=f"0x{protocol_number:02X}",
            elapsed_ms=self.elapsed_ms,
        )

    def on_ack_sent(self, ack: bytes) -> None:
        self.on_tx(ack)
        self._emit(
            logging.INFO,
            "ACK_SENT",
            event="ACK_SENT",
            bytes=len(ack),
            elapsed_ms=self.elapsed_ms,
            **(
                {"hex": bytes_to_hex(ack), "ascii": bytes_to_ascii(ack)}
                if logger.isEnabledFor(logging.INFO)
                else {}
            ),
        )

    def on_exception(
        self,
        exc: BaseException,
        *,
        close_reason: str = CLOSE_EXCEPTION,
        affects_close: bool = True,
    ) -> None:
        EXCEPTIONS_TOTAL.inc()
        if affects_close:
            self.close_reason = self.close_reason or close_reason
        fields: dict[str, Any] = {
            "event": "EXCEPTION",
            "elapsed_ms": self.elapsed_ms,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ),
        }
        if affects_close:
            fields["close_reason"] = close_reason
        if self.last_rx is not None and logger.isEnabledFor(logging.ERROR):
            fields["last_rx_hex"] = bytes_to_hex(self.last_rx)
            fields["last_rx_bytes"] = len(self.last_rx)
        if self.last_tx is not None and logger.isEnabledFor(logging.ERROR):
            fields["last_tx_hex"] = bytes_to_hex(self.last_tx)
            fields["last_tx_bytes"] = len(self.last_tx)
        self._emit(logging.ERROR, "EXCEPTION", **fields)

    def set_close_reason(self, reason: str) -> None:
        if self.close_reason is None:
            self.close_reason = reason

    def on_close(self, active_count: int) -> None:
        if self._closed:
            return
        self._closed = True
        reason = self.close_reason or CLOSE_SERVER
        SESSIONS_CLOSED_TOTAL.labels(reason=reason).inc()
        CONNECTIONS_ACTIVE.set(active_count)
        TCP_CONNECTIONS_ACTIVE.set(active_count)
        self._emit(
            logging.INFO,
            "CLOSE",
            event="CLOSE",
            close_reason=reason,
            duration_ms=self.elapsed_ms,
            elapsed_ms=self.elapsed_ms,
            time_to_first_byte_ms=self.time_to_first_byte_ms,
            bytes_rx=self.bytes_rx,
            bytes_tx=self.bytes_tx,
            reads=self.reads,
            writes=self.writes,
        )

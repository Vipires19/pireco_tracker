"""Session Recorder — captura integral de eventos em Learning Mode."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from app.observability.formatting import bytes_to_ascii, bytes_to_hex


class SessionRecorder:
    """Acumula eventos de uma sessão desconhecida para análise offline."""

    def __init__(
        self,
        *,
        session_id: str,
        remote_ip: str,
        remote_port: int,
        connected_at: datetime | None = None,
    ) -> None:
        self.session_id = session_id
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.started_at = connected_at or datetime.now(UTC)
        self.finished_at: datetime | None = None
        self.protocol_detected = "unknown"
        self.close_reason: str | None = None
        self._connected_mono = time.monotonic()
        self._events: list[dict[str, Any]] = []

    @property
    def elapsed_ms(self) -> float:
        return round((time.monotonic() - self._connected_mono) * 1000, 3)

    @property
    def duration_ms(self) -> float | None:
        if self.finished_at is None:
            return None
        return round((self.finished_at - self.started_at).total_seconds() * 1000, 3)

    def _append(self, event: str, **fields: Any) -> None:
        payload: dict[str, Any] = {
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "elapsed_ms": fields.pop("elapsed_ms", self.elapsed_ms),
            "session_id": self.session_id,
            "remote_ip": self.remote_ip,
            "remote_port": self.remote_port,
        }
        payload.update(fields)
        self._events.append(payload)

    def record_connect(self) -> None:
        self._append(
            "CONNECT",
            elapsed_ms=0.0,
            protocol_detected=self.protocol_detected,
            learning_mode=True,
        )

    def record_rx(self, data: bytes, *, elapsed_ms: float | None = None) -> None:
        # Learning Mode exige hex/ascii completos na gravação (storage ≠ logging).
        self._append(
            "RX",
            bytes=len(data),
            hex=bytes_to_hex(data),
            ascii=bytes_to_ascii(data),
            elapsed_ms=self.elapsed_ms if elapsed_ms is None else elapsed_ms,
        )

    def record_tx(self, data: bytes, *, elapsed_ms: float | None = None) -> None:
        self._append(
            "TX",
            bytes=len(data),
            hex=bytes_to_hex(data),
            ascii=bytes_to_ascii(data),
            elapsed_ms=self.elapsed_ms if elapsed_ms is None else elapsed_ms,
        )

    def record_timeout(self, *, message: str | None = None) -> None:
        fields: dict[str, Any] = {}
        if message:
            fields["message"] = message
        self._append("TIMEOUT", **fields)

    def record_exception(self, exc: BaseException, *, traceback_text: str | None = None) -> None:
        fields: dict[str, Any] = {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        if traceback_text:
            fields["traceback"] = traceback_text
        self._append("EXCEPTION", **fields)

    def record_close(self, close_reason: str) -> None:
        self.close_reason = close_reason
        self._append("CLOSE", close_reason=close_reason, duration_ms=self.elapsed_ms)

    def finish(self, close_reason: str) -> dict[str, Any]:
        if self.finished_at is None:
            self.finished_at = datetime.now(UTC)
            if not any(e.get("event") == "CLOSE" for e in self._events):
                self.record_close(close_reason)
            else:
                self.close_reason = close_reason
        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        finished = self.finished_at or datetime.now(UTC)
        duration = round((finished - self.started_at).total_seconds() * 1000, 3)
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished.isoformat(),
            "remote_ip": self.remote_ip,
            "remote_port": self.remote_port,
            "protocol_detected": self.protocol_detected,
            "close_reason": self.close_reason,
            "duration_ms": duration,
            "learning_mode": True,
            "events": list(self._events),
        }

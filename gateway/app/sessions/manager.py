"""Gerenciamento de sessões TCP ativas — fonte de verdade das conexões."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.core.observability import log_with_fields
from app.observability.formatting import bytes_to_ascii, bytes_to_hex
from app.observability.metrics import TX_BYTES_TOTAL

logger = get_logger(__name__)


@dataclass
class DeviceSession:
    connection_id: str
    remote_ip: str
    writer: Any
    imei: str | None = None
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_heartbeat: datetime | None = None
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.last_activity = datetime.now(UTC)

    def record_heartbeat(self) -> None:
        now = datetime.now(UTC)
        self.last_heartbeat = now
        self.last_activity = now


class SessionManager:
    """Controla conexões ativas e mapeamento IMEI ↔ sessão TCP."""

    def __init__(self) -> None:
        self._sessions: dict[str, DeviceSession] = {}
        self._imei_index: dict[str, str] = {}
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    async def register(self, connection_id: str, remote_ip: str, writer: Any) -> DeviceSession:
        session = DeviceSession(
            connection_id=connection_id,
            remote_ip=remote_ip,
            writer=writer,
        )
        async with self._lock:
            self._sessions[connection_id] = session
        logger.info("Session registered id=%s remote_ip=%s", connection_id, remote_ip)
        return session

    async def bind_imei(self, connection_id: str, imei: str) -> None:
        async with self._lock:
            session = self._sessions.get(connection_id)
            if session is None:
                return

            previous = self._imei_index.get(imei)
            if previous and previous != connection_id:
                logger.warning(
                    "IMEI %s moved from connection %s to %s",
                    imei,
                    previous,
                    connection_id,
                )

            session.imei = imei
            session.touch()
            self._imei_index[imei] = connection_id
        logger.info("IMEI bound id=%s imei=%s", connection_id, imei)

    async def get_by_connection(self, connection_id: str) -> DeviceSession | None:
        return self._sessions.get(connection_id)

    async def get_by_imei(self, imei: str) -> DeviceSession | None:
        connection_id = self._imei_index.get(imei)
        if connection_id is None:
            return None
        return self._sessions.get(connection_id)

    async def record_heartbeat(self, connection_id: str) -> None:
        session = self._sessions.get(connection_id)
        if session is not None:
            session.record_heartbeat()

    async def touch(self, connection_id: str) -> None:
        session = self._sessions.get(connection_id)
        if session is not None:
            session.touch()

    async def remove(self, connection_id: str) -> DeviceSession | None:
        async with self._lock:
            session = self._sessions.pop(connection_id, None)
            if session is None:
                return None

            if session.imei and self._imei_index.get(session.imei) == connection_id:
                del self._imei_index[session.imei]

        logger.info(
            "Session removed id=%s imei=%s remote_ip=%s",
            connection_id,
            session.imei or "unknown",
            session.remote_ip,
        )
        return session

    async def send_to_imei(self, imei: str, payload: bytes) -> bool:
        session = await self.get_by_imei(imei)
        if session is None:
            logger.warning("Cannot send command — IMEI not connected imei=%s", imei)
            return False

        try:
            session.writer.write(payload)
            await session.writer.drain()
            session.touch()
            TX_BYTES_TOTAL.inc(len(payload))
            tx_fields: dict[str, Any] = {
                "event": "TX",
                "session_id": session.connection_id,
                "remote_ip": session.remote_ip,
                "protocol": "gt06",
                "bytes": len(payload),
                "source": "command",
            }
            if logger.isEnabledFor(logging.INFO):
                tx_fields["hex"] = bytes_to_hex(payload)
                tx_fields["ascii"] = bytes_to_ascii(payload)
            log_with_fields(logger, logging.INFO, "TX", **tx_fields)
            return True
        except Exception:
            logger.exception("Failed to send command imei=%s", imei)
            return False

    async def list_sessions(self) -> list[dict[str, str | None]]:
        return [
            {
                "connection_id": session.connection_id,
                "imei": session.imei,
                "remote_ip": session.remote_ip,
                "last_heartbeat": (
                    session.last_heartbeat.isoformat() if session.last_heartbeat else None
                ),
            }
            for session in self._sessions.values()
        ]


session_manager = SessionManager()

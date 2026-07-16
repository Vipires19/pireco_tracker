import json
from datetime import UTC, datetime

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.messages import (
    DeviceConnection,
    DeviceEvent,
    DeviceHeartbeat,
    DevicePosition,
    DomainMessage,
)
from app.core.observability import bind_context, get_logger, log_with_fields
from app.exceptions import DuplicateEventError

from app.config import get_settings
from app.models.entities import DeviceEvent as DeviceEventModel
from app.models.entities import Position, ProcessedEvent, Tracker
from app.observability.metrics import EVENTS_DUPLICATE, EVENTS_PERSISTED

logger = get_logger(__name__)

HEALTH_ONLINE = "ONLINE"


def _normalize_ip(remote_ip: str | None) -> str | None:
    """Persiste apenas o host (sem porta efêmera do peer TCP)."""
    if not remote_ip:
        return None
    value = remote_ip.strip()
    if not value or value == "unknown":
        return None
    if value.startswith("[") and "]" in value:
        return value[1 : value.index("]")]
    if value.count(":") == 1:
        host, _, _port = value.partition(":")
        return host or value
    return value


class PersistenceService:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def process(self, session: AsyncSession, message: DomainMessage) -> None:
        bind_context(
            trace_id=message.trace_id,
            imei=message.tracker_imei,
            event_type=message.message_type.value,
        )

        if await self._is_duplicate(session, message):
            EVENTS_DUPLICATE.inc()
            raise DuplicateEventError(
                "Duplicate event",
                details={"dedup_key": message.dedup_key()},
            )

        tracker = await self._find_tracker(session, message.tracker_imei)
        if tracker is None:
            log_with_fields(
                logger,
                30,
                "Device not registered",
                imei=message.tracker_imei,
                protocol=message.source_protocol,
                remote_ip=message.remote_ip,
                message_type=message.message_type.value,
            )
            await self._mark_processed(session, message)
            return

        should_sync = isinstance(message, (DevicePosition, DeviceHeartbeat)) or (
            isinstance(message, DeviceConnection) and message.action == "login"
        )
        if should_sync:
            await self._sync_device(tracker, message)

        await self._update_session_cache(message)

        if isinstance(message, DevicePosition):
            await self._handle_position(session, tracker, message)
        elif isinstance(message, DeviceHeartbeat):
            await self._handle_heartbeat(session, message)
        elif isinstance(message, DeviceEvent):
            await self._handle_event(session, tracker, message)
        elif isinstance(message, DeviceConnection):
            await self._handle_connection(session, message)

        await self._mark_processed(session, message)
        EVENTS_PERSISTED.labels(message_type=message.message_type.value).inc()

    async def _is_duplicate(self, session: AsyncSession, message: DomainMessage) -> bool:
        dedup_key = message.dedup_key()
        result = await session.execute(
            select(ProcessedEvent).where(ProcessedEvent.dedup_key == dedup_key)
        )
        return result.scalar_one_or_none() is not None

    async def _mark_processed(self, session: AsyncSession, message: DomainMessage) -> None:
        session.add(
            ProcessedEvent(
                dedup_key=message.dedup_key(),
                trace_id=message.trace_id,
                tracker_imei=message.tracker_imei,
                message_type=message.message_type.value,
            )
        )

    async def _find_tracker(self, session: AsyncSession, imei: str) -> Tracker | None:
        result = await session.execute(
            select(Tracker).where(Tracker.imei == imei, Tracker.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def _sync_device(self, tracker: Tracker, message: DomainMessage) -> None:
        """Atualiza estado ERP do dispositivo a partir da telemetria (sem auto-create)."""
        now = message.received_at
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        tracker.last_seen_at = now
        tracker.health_status = HEALTH_ONLINE
        tracker.updated_at = datetime.now(UTC)

        ip = _normalize_ip(message.remote_ip)
        if ip:
            tracker.last_ip = ip
            tracker.last_remote_ip = ip

        if message.source_protocol and message.source_protocol != "unknown":
            tracker.protocol = message.source_protocol.strip().lower()

        if isinstance(message, DeviceConnection) and message.action == "login":
            if message.manufacturer:
                tracker.manufacturer = message.manufacturer
            if message.model:
                tracker.model = message.model
            if message.firmware:
                tracker.firmware = message.firmware

        if isinstance(message, DevicePosition):
            if message.latitude is not None and message.longitude is not None:
                tracker.last_latitude = message.latitude
                tracker.last_longitude = message.longitude
                tracker.last_speed = message.speed_kmh
                tracker.last_course = message.course_degrees
                tracker.last_gps_time = message.gps_time or now

    async def _update_session_cache(self, message: DomainMessage) -> None:
        settings = get_settings()
        key = f"{settings.redis_session_key_prefix}{message.tracker_imei}"
        payload = {
            "tracker_imei": message.tracker_imei,
            "trace_id": message.trace_id,
            "connection_id": message.connection_id,
            "remote_ip": _normalize_ip(message.remote_ip) or message.remote_ip,
            "last_seen_at": message.received_at.isoformat(),
            "message_type": message.message_type.value,
            "protocol": message.source_protocol,
        }
        await self._redis.set(key, json.dumps(payload), ex=3600)

    async def _handle_position(
        self, session: AsyncSession, tracker: Tracker, message: DevicePosition
    ) -> None:
        position = Position(
            tracker_id=tracker.id,
            tracker_imei=message.tracker_imei,
            trace_id=message.trace_id,
            latitude=message.latitude,
            longitude=message.longitude,
            speed_kmh=message.speed_kmh,
            course_degrees=message.course_degrees,
            gps_time=message.gps_time,
            received_at=message.received_at,
            connection_id=message.connection_id,
            remote_ip=_normalize_ip(message.remote_ip) or message.remote_ip,
        )
        session.add(position)

    async def _handle_heartbeat(self, session: AsyncSession, message: DeviceHeartbeat) -> None:
        log_with_fields(logger, 20, "Heartbeat processed", gsm_signal=message.gsm_signal)

    async def _handle_event(
        self, session: AsyncSession, tracker: Tracker, message: DeviceEvent
    ) -> None:
        session.add(
            DeviceEventModel(
                tracker_id=tracker.id,
                tracker_imei=message.tracker_imei,
                trace_id=message.trace_id,
                event_code=message.event_code,
                event_category=message.event_category,
                event_metadata=message.metadata or None,
                received_at=message.received_at,
                connection_id=message.connection_id,
                remote_ip=_normalize_ip(message.remote_ip) or message.remote_ip,
            )
        )

    async def _handle_connection(
        self, session: AsyncSession, message: DeviceConnection
    ) -> None:
        if message.action == "disconnect":
            settings = get_settings()
            key = f"{settings.redis_session_key_prefix}{message.tracker_imei}"
            await self._redis.delete(key)

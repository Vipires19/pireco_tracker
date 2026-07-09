import traceback
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
from app.exceptions import DuplicateEventError, PersistenceError
from app.core.observability import bind_context, get_logger, log_with_fields

from app.config import get_settings
from app.models.entities import DeviceEvent as DeviceEventModel
from app.models.entities import Position, ProcessedEvent, Tracker
from app.observability.metrics import EVENTS_DUPLICATE, EVENTS_PERSISTED

logger = get_logger(__name__)


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

        tracker = await self._ensure_tracker(session, message)
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

    async def _ensure_tracker(self, session: AsyncSession, message: DomainMessage) -> Tracker:
        result = await session.execute(
            select(Tracker).where(Tracker.imei == message.tracker_imei)
        )
        tracker = result.scalar_one_or_none()

        if tracker is None:
            tracker = Tracker(company_id=1, imei=message.tracker_imei, is_active=True)
            session.add(tracker)
            await session.flush()
            log_with_fields(logger, 20, "Tracker auto-provisioned", tracker_id=tracker.id)

        tracker.last_seen_at = message.received_at
        tracker.last_remote_ip = message.remote_ip
        return tracker

    async def _update_session_cache(self, message: DomainMessage) -> None:
        import json

        settings = get_settings()
        key = f"{settings.redis_session_key_prefix}{message.tracker_imei}"
        payload = {
            "tracker_imei": message.tracker_imei,
            "trace_id": message.trace_id,
            "connection_id": message.connection_id,
            "remote_ip": message.remote_ip,
            "last_seen_at": message.received_at.isoformat(),
            "message_type": message.message_type.value,
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
            remote_ip=message.remote_ip,
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
                remote_ip=message.remote_ip,
            )
        )

    async def _handle_connection(
        self, session: AsyncSession, message: DeviceConnection
    ) -> None:
        if message.action == "disconnect":
            settings = get_settings()
            key = f"{settings.redis_session_key_prefix}{message.tracker_imei}"
            await self._redis.delete(key)

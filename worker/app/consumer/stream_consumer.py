import asyncio
import time
import traceback
from datetime import UTC, datetime

import redis.asyncio as redis
from redis.exceptions import ResponseError

from app.contracts.messages import parse_stream_fields
from app.exceptions import DuplicateEventError, PersistenceError, TrackerError
from app.core.observability import bind_context, get_logger, log_with_fields

from app.config import get_settings
from app.consumer.dlq import DeadLetterQueue
from app.core.database import db_manager
from app.handlers.message_handler import MessageHandler
from app.observability.metrics import (
    DB_LATENCY,
    EVENTS_CONSUMED,
    EVENTS_FAILED,
    EVENTS_RETRIED,
    PIPELINE_LATENCY,
    THROUGHPUT,
)

logger = get_logger(__name__)


class StreamConsumer:
    def __init__(
        self,
        redis_client: redis.Redis,
        handler: MessageHandler,
        dlq: DeadLetterQueue,
    ) -> None:
        self._redis = redis_client
        self._handler = handler
        self._dlq = dlq
        self._settings = get_settings()
        self._running = False

    async def ensure_consumer_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                self._settings.redis_stream_key,
                self._settings.redis_consumer_group,
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def run(self) -> None:
        self._running = True
        await self.ensure_consumer_group()
        log_with_fields(logger, 20, "Stream consumer started")

        while self._running:
            try:
                entries = await self._redis.xreadgroup(
                    groupname=self._settings.redis_consumer_group,
                    consumername=self._settings.redis_consumer_name,
                    streams={self._settings.redis_stream_key: ">"},
                    count=self._settings.redis_stream_read_count,
                    block=self._settings.redis_stream_block_ms,
                )
            except redis.RedisError:
                logger.exception("Error reading from stream")
                await asyncio.sleep(1)
                continue

            if not entries:
                continue

            for _stream_name, messages in entries:
                for message_id, fields in messages:
                    await self._process_with_retry(message_id, fields)

    async def _process_with_retry(self, message_id: str, fields: dict[str, str]) -> None:
        settings = self._settings
        max_retries = settings.worker_max_retries

        for attempt in range(1, max_retries + 1):
            try:
                await self._process_message(message_id, fields)
                return
            except DuplicateEventError:
                await self._ack(message_id)
                return
            except (PersistenceError, TrackerError) as exc:
                if attempt < max_retries:
                    EVENTS_RETRIED.inc()
                    log_with_fields(
                        logger,
                        30,
                        "Retrying message",
                        message_id=message_id,
                        attempt=attempt,
                        error=str(exc),
                    )
                    await asyncio.sleep(settings.worker_retry_backoff_ms / 1000 * attempt)
                else:
                    await self._dlq.send(
                        original_id=message_id,
                        fields=fields,
                        reason=str(exc),
                        retry_count=attempt,
                        exc=exc,
                    )
                    await self._ack(message_id)
            except Exception as exc:
                EVENTS_FAILED.inc()
                await self._dlq.send(
                    original_id=message_id,
                    fields=fields,
                    reason=str(exc),
                    retry_count=attempt,
                    exc=exc,
                )
                await self._ack(message_id)
                return

    async def _process_message(self, message_id: str, fields: dict[str, str]) -> None:
        message = parse_stream_fields(fields)
        if message is None:
            log_with_fields(logger, 30, "Unparseable message", message_id=message_id)
            await self._ack(message_id)
            return

        bind_context(trace_id=message.trace_id, imei=message.tracker_imei)
        EVENTS_CONSUMED.labels(message_type=message.message_type.value).inc()

        published_at = fields.get("published_at")
        if published_at:
            try:
                pub_dt = datetime.fromisoformat(published_at)
                PIPELINE_LATENCY.observe(max((datetime.now(UTC) - pub_dt).total_seconds(), 0))
            except ValueError:
                pass

        if db_manager._session_factory is None:
            raise PersistenceError("Database not initialized")

        start = time.perf_counter()
        async with db_manager._session_factory() as session:
            await self._handler.handle(session, message)
            await session.commit()
        DB_LATENCY.observe(time.perf_counter() - start)

        await self._ack(message_id)
        THROUGHPUT.inc()
        log_with_fields(
            logger,
            20,
            "Message processed",
            message_id=message_id,
            message_type=message.message_type.value,
        )

    async def _ack(self, message_id: str) -> None:
        await self._redis.xack(
            self._settings.redis_stream_key,
            self._settings.redis_consumer_group,
            message_id,
        )

    async def stop(self) -> None:
        self._running = False

import time
from datetime import UTC, datetime

import redis.asyncio as redis

from app.contracts.messages import DomainMessage, serialize_contract
from app.exceptions import PublishEventError
from app.core.observability import bind_context, get_logger, log_with_fields

from app.config import get_settings
from app.observability.metrics import EVENTS_PUBLISHED, PUBLISH_LATENCY

logger = get_logger(__name__)


class RedisEventPublisher:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        settings = get_settings()
        self._client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        await self._client.ping()
        log_with_fields(logger, 20, "Redis publisher connected")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ping(self) -> bool:
        if self._client is None:
            return False
        return bool(await self._client.ping())

    async def publish(self, message: DomainMessage) -> str | None:
        if self._client is None:
            raise PublishEventError("Redis publisher not connected")

        settings = get_settings()
        fields = serialize_contract(message)
        fields["published_at"] = datetime.now(UTC).isoformat()

        bind_context(
            trace_id=message.trace_id,
            imei=message.tracker_imei,
            event_type=message.message_type.value,
        )

        start = time.perf_counter()
        try:
            message_id = await self._client.xadd(
                settings.redis_stream_key,
                fields,
                maxlen=settings.redis_stream_maxlen,
                approximate=True,
            )
        except redis.RedisError as exc:
            raise PublishEventError(str(exc)) from exc

        elapsed = time.perf_counter() - start
        PUBLISH_LATENCY.observe(elapsed)
        EVENTS_PUBLISHED.labels(message_type=message.message_type.value).inc()

        log_with_fields(
            logger,
            20,
            "Event published",
            stream=settings.redis_stream_key,
            message_id=message_id,
            message_type=message.message_type.value,
            latency_ms=round(elapsed * 1000, 2),
        )
        return message_id


event_publisher = RedisEventPublisher()

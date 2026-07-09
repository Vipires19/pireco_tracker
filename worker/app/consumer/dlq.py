"""Dead Letter Queue — nenhum evento perdido."""

import traceback
from datetime import UTC, datetime

import redis.asyncio as redis

from app.core.observability import get_logger, log_with_fields

from app.config import get_settings
from app.observability.metrics import EVENTS_DLQ

logger = get_logger(__name__)


class DeadLetterQueue:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def send(
        self,
        *,
        original_id: str,
        fields: dict[str, str],
        reason: str,
        retry_count: int,
        exc: Exception | None = None,
    ) -> str:
        settings = get_settings()
        dlq_fields = {
            **fields,
            "original_stream_id": original_id,
            "failure_reason": reason[:500],
            "stacktrace": traceback.format_exc()[:2000] if exc else "",
            "retry_count": str(retry_count),
            "failed_at": datetime.now(UTC).isoformat(),
        }
        message_id = await self._redis.xadd(
            settings.redis_dead_letter_stream_key,
            dlq_fields,
            maxlen=settings.redis_stream_maxlen,
            approximate=True,
        )
        EVENTS_DLQ.inc()
        log_with_fields(
            logger,
            40,
            "Event sent to DLQ",
            original_id=original_id,
            reason=reason,
            retry_count=retry_count,
            dlq_id=message_id,
        )
        return message_id

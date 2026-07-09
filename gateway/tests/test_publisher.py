from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.contracts.messages import SCHEMA_VERSION
from app.contracts.messages import DeviceHeartbeat


@pytest.mark.asyncio
async def test_publish_adds_published_at() -> None:
    from app.publisher.redis_publisher import RedisEventPublisher

    publisher = RedisEventPublisher()
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1234-0")
    publisher._client = mock_redis

    message = DeviceHeartbeat(
        schema_version=SCHEMA_VERSION,
        trace_id="trace-1",
        tracker_imei="867686031234567",
        received_at=datetime.now(UTC),
        connection_id="c1",
        remote_ip="127.0.0.1",
    )

    with patch("app.publisher.redis_publisher.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            redis_stream_key="tracker:events",
            redis_stream_maxlen=1000,
        )
        message_id = await publisher.publish(message)

    assert message_id == "1234-0"
    fields = mock_redis.xadd.call_args[0][1]
    assert fields["message_type"] == "heartbeat"
    assert fields["trace_id"] == "trace-1"
    assert "published_at" in fields

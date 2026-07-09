from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.contracts.messages import SCHEMA_VERSION
from app.contracts.messages import DevicePosition

from app.models.entities import Tracker
from app.services.persistence import PersistenceService


@pytest.mark.asyncio
async def test_persist_position() -> None:
    redis = AsyncMock()
    service = PersistenceService(redis)

    tracker = Tracker(id=1, company_id=1, imei="867686031234567", is_active=True)
    session = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.side_effect = [None, None, tracker]
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.flush = AsyncMock()

    message = DevicePosition(
        schema_version=SCHEMA_VERSION,
        trace_id="trace-1",
        tracker_imei="867686031234567",
        connection_id="c1",
        remote_ip="127.0.0.1",
        received_at=datetime.now(UTC),
        latitude=-23.550520,
        longitude=-46.633308,
        speed_kmh=45.0,
        course_degrees=180,
        serial_number=3,
        payload_hash="hash1",
    )

    await service.process(session, message)
    assert session.add.call_count >= 2
    redis.set.assert_called_once()

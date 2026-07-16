from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.contracts.messages import SCHEMA_VERSION, DeviceConnection, DeviceHeartbeat, DevicePosition
from app.models.entities import Tracker
from app.services.persistence import HEALTH_ONLINE, PersistenceService


def _tracker(**extra: object) -> Tracker:
    return Tracker(
        id=1,
        company_id=1,
        imei="867686031234567",
        is_active=True,
        health_status="UNKNOWN",
        **extra,
    )


def _session_with_tracker(tracker: Tracker | None) -> AsyncMock:
    session = AsyncMock()
    result_mock = MagicMock()
    # 1) duplicate check → None; 2) find tracker
    result_mock.scalar_one_or_none.side_effect = [None, tracker]
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_persist_position_syncs_device() -> None:
    redis = AsyncMock()
    service = PersistenceService(redis)
    tracker = _tracker()
    session = _session_with_tracker(tracker)
    now = datetime.now(UTC)

    message = DevicePosition(
        schema_version=SCHEMA_VERSION,
        trace_id="trace-1",
        tracker_imei="867686031234567",
        connection_id="c1",
        remote_ip="127.0.0.1",
        source_protocol="gt06",
        received_at=now,
        latitude=-23.550520,
        longitude=-46.633308,
        speed_kmh=45.0,
        course_degrees=180,
        gps_time=now,
        serial_number=3,
        payload_hash="hash1",
    )

    await service.process(session, message)

    assert tracker.last_seen_at == now
    assert tracker.last_ip == "127.0.0.1"
    assert tracker.protocol == "gt06"
    assert tracker.health_status == HEALTH_ONLINE
    assert tracker.last_latitude == -23.550520
    assert tracker.last_longitude == -46.633308
    assert tracker.last_speed == 45.0
    assert tracker.last_course == 180
    assert session.add.call_count >= 2
    redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_heartbeat_keeps_device_online() -> None:
    redis = AsyncMock()
    service = PersistenceService(redis)
    tracker = _tracker()
    session = _session_with_tracker(tracker)
    now = datetime.now(UTC)

    message = DeviceHeartbeat(
        schema_version=SCHEMA_VERSION,
        trace_id="trace-hb",
        tracker_imei="867686031234567",
        connection_id="c1",
        remote_ip="10.0.0.2",
        source_protocol="gt06",
        received_at=now,
        terminal_info="0",
        voltage_level="6",
        gsm_signal=4,
        serial_number=2,
    )

    await service.process(session, message)

    assert tracker.last_seen_at == now
    assert tracker.health_status == HEALTH_ONLINE
    assert tracker.last_ip == "10.0.0.2"
    assert tracker.protocol == "gt06"


@pytest.mark.asyncio
async def test_login_updates_last_seen() -> None:
    redis = AsyncMock()
    service = PersistenceService(redis)
    tracker = _tracker()
    session = _session_with_tracker(tracker)
    now = datetime.now(UTC)

    message = DeviceConnection(
        schema_version=SCHEMA_VERSION,
        trace_id="trace-login",
        tracker_imei="867686031234567",
        connection_id="c1",
        remote_ip="192.168.1.10",
        source_protocol="gt06",
        received_at=now,
        action="login",
    )

    await service.process(session, message)

    assert tracker.last_seen_at == now
    assert tracker.health_status == HEALTH_ONLINE
    assert tracker.last_ip == "192.168.1.10"
    assert tracker.protocol == "gt06"


@pytest.mark.asyncio
async def test_unregistered_device_is_not_created() -> None:
    redis = AsyncMock()
    service = PersistenceService(redis)
    session = _session_with_tracker(None)
    now = datetime.now(UTC)

    message = DevicePosition(
        schema_version=SCHEMA_VERSION,
        trace_id="trace-unknown",
        tracker_imei="867686039999999",
        connection_id="c1",
        remote_ip="127.0.0.1",
        source_protocol="gt06",
        received_at=now,
        latitude=-23.0,
        longitude=-46.0,
        speed_kmh=10.0,
        course_degrees=90,
        serial_number=1,
        payload_hash="hash-unknown",
    )

    await service.process(session, message)

    # apenas processed_events — sem Position e sem auto-create
    assert session.add.call_count == 1
    redis.set.assert_not_called()

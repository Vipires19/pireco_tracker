from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.devices.models import HealthStatus
from app.domains.monitoring.services.monitoring_service import MonitoringService


def _build_row(*, last_seen_at: datetime | None, lat: float | None = None, lng: float | None = None):
    tracker = MagicMock()
    tracker.id = 10
    tracker.imei = "867123456789012"
    tracker.model = "GT06N"
    tracker.last_seen_at = last_seen_at
    tracker.last_latitude = lat
    tracker.last_longitude = lng
    tracker.last_speed = 30.0
    tracker.last_course = 90
    tracker.last_gps_time = datetime.now(UTC)

    vehicle = MagicMock()
    vehicle.id = 5
    vehicle.plate = "ABC1D23"
    vehicle.model = "Onix"
    vehicle.brand = "Chevrolet"
    vehicle.nickname = None

    customer = MagicMock()
    customer.id = 1
    customer.full_name = "Cliente Teste"

    assignment = MagicMock()
    return assignment, tracker, vehicle, customer


@pytest.mark.asyncio
async def test_monitoring_service_maps_health_from_last_seen() -> None:
    service = MonitoringService(session=AsyncMock())
    service._repository.list_installed_vehicles = AsyncMock(
        return_value=[_build_row(last_seen_at=datetime.now(UTC) - timedelta(seconds=30))]
    )

    items = await service.list_vehicles()
    assert len(items) == 1
    assert items[0].health == HealthStatus.ONLINE
    assert items[0].vehicle_id == 5
    assert items[0].tracker_imei == "867123456789012"


@pytest.mark.asyncio
async def test_monitoring_service_unknown_without_last_seen() -> None:
    service = MonitoringService(session=AsyncMock())
    service._repository.list_installed_vehicles = AsyncMock(
        return_value=[_build_row(last_seen_at=None, lat=None, lng=None)]
    )

    items = await service.list_vehicles()
    assert items[0].health == HealthStatus.UNKNOWN
    assert items[0].latitude is None
    assert items[0].longitude is None

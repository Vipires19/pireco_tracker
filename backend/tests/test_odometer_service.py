import pytest

from app.domains.fleet.services.odometer_service import GeoPoint, haversine_km, segment_distance_km


def test_haversine_known_distance() -> None:
    # São Paulo centro ~ Rio centro ≈ 357 km (ordem de grandeza)
    sp = GeoPoint(latitude=-23.5505, longitude=-46.6333)
    rj = GeoPoint(latitude=-22.9068, longitude=-43.1729)
    distance = haversine_km(sp, rj)
    assert 340 < distance < 380


def test_segment_distance_ignores_gps_noise() -> None:
    a = GeoPoint(latitude=-23.5505, longitude=-46.6333)
    b = GeoPoint(latitude=-23.55051, longitude=-46.63331)
    assert segment_distance_km(a, b) == 0.0


@pytest.mark.asyncio
async def test_odometer_recalculation_not_implemented() -> None:
    from app.domains.fleet.services import OdometerService

    service = OdometerService(session=None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        await service.recalculate_vehicle_odometer(1)

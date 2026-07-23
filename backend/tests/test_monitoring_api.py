import random
import time
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.core.database import db_manager
from app.domains.devices.models import Tracker

BASE = "/api/v1"


def _unique_imei() -> str:
    suffix = int(time.time() * 1_000_000) % 10**12
    return f"867{suffix:012d}"[:15].ljust(15, "0")


def _unique_document() -> str:
    return f"9{int(time.time() * 1000) % 10**10:010d}"


def _unique_plate() -> str:
    return f"MON{random.randint(0, 9)}{chr(65 + random.randint(0, 25))}{random.randint(0, 99):02d}"


async def _login(client: AsyncClient) -> str:
    response = await client.post(
        f"{BASE}/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _create_customer(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.post(
        f"{BASE}/customers",
        headers=headers,
        json={
            "full_name": f"Cliente Monitoring {int(time.time())}",
            "document": _unique_document(),
            "document_type": "CPF",
            "phone": "(11) 98765-4321",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_vehicle(client: AsyncClient, headers: dict[str, str], customer_id: int) -> int:
    response = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json={
            "customer_id": customer_id,
            "plate": _unique_plate(),
            "model": "Onix",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_tracker(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json={
            "imei": _unique_imei(),
            "model": "GT06N",
            "status": "IN_STOCK",
            "origin": "MANUAL",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _install_tracker(
    client: AsyncClient,
    headers: dict[str, str],
    tracker_id: int,
    vehicle_id: int,
) -> None:
    response = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json={
            "tracker_id": tracker_id,
            "vehicle_id": vehicle_id,
            "installation_type": "PRIMARY",
            "checklist": {
                "power_connected": True,
                "gps_ok": True,
                "gsm_ok": True,
                "customer_present": True,
            },
            "complete": True,
        },
    )
    assert response.status_code == 201, response.text


async def _set_tracker_telemetry(
    tracker_id: int,
    *,
    last_seen_at: datetime | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    speed: float | None = None,
    course: int | None = None,
) -> None:
    values: dict = {}
    if last_seen_at is not None:
        values["last_seen_at"] = last_seen_at
    if latitude is not None:
        values["last_latitude"] = latitude
    if longitude is not None:
        values["last_longitude"] = longitude
    if speed is not None:
        values["last_speed"] = speed
    if course is not None:
        values["last_course"] = course
    if latitude is not None and longitude is not None:
        values["last_gps_time"] = datetime.now(UTC)

    async for session in db_manager.get_session():
        await session.execute(update(Tracker).where(Tracker.id == tracker_id).values(**values))
        await session.commit()
        break


@pytest.mark.asyncio
async def test_monitoring_vehicles_requires_jwt(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/monitoring/vehicles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_monitoring_vehicles_lists_installed_with_position(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)
    await _install_tracker(client, headers, tracker_id, vehicle_id)
    await _set_tracker_telemetry(
        tracker_id,
        last_seen_at=datetime.now(UTC) - timedelta(seconds=20),
        latitude=-21.177,
        longitude=-47.810,
        speed=38,
        course=124,
    )

    response = await client.get(f"{BASE}/monitoring/vehicles", headers=headers)
    assert response.status_code == 200
    items = response.json()
    match = next((item for item in items if item["vehicle_id"] == vehicle_id), None)
    assert match is not None
    assert match["plate"]
    assert match["model"] == "Onix"
    assert match["customer_name"]
    assert match["tracker_id"] == tracker_id
    assert match["tracker_imei"]
    assert match["health"] == "ONLINE"
    assert match["latitude"] == pytest.approx(-21.177)
    assert match["longitude"] == pytest.approx(-47.810)
    assert match["speed"] == pytest.approx(38)
    assert match["course"] == 124
    assert match["last_seen_at"] is not None
    assert match["gps_time"] is not None


@pytest.mark.asyncio
async def test_monitoring_vehicles_without_position(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)
    await _install_tracker(client, headers, tracker_id, vehicle_id)

    response = await client.get(f"{BASE}/monitoring/vehicles", headers=headers)
    assert response.status_code == 200
    match = next((item for item in response.json() if item["vehicle_id"] == vehicle_id), None)
    assert match is not None
    assert match["latitude"] is None
    assert match["longitude"] is None
    assert match["health"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_monitoring_vehicles_offline_health(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)
    await _install_tracker(client, headers, tracker_id, vehicle_id)
    await _set_tracker_telemetry(
        tracker_id,
        last_seen_at=datetime.now(UTC) - timedelta(seconds=300),
        latitude=-21.0,
        longitude=-47.0,
    )

    response = await client.get(f"{BASE}/monitoring/vehicles", headers=headers)
    assert response.status_code == 200
    match = next((item for item in response.json() if item["vehicle_id"] == vehicle_id), None)
    assert match is not None
    assert match["health"] == "OFFLINE"


@pytest.mark.asyncio
async def test_monitoring_vehicles_unknown_health(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)
    await _install_tracker(client, headers, tracker_id, vehicle_id)

    response = await client.get(f"{BASE}/monitoring/vehicles", headers=headers)
    assert response.status_code == 200
    match = next((item for item in response.json() if item["vehicle_id"] == vehicle_id), None)
    assert match is not None
    assert match["health"] == "UNKNOWN"
    assert match["last_seen_at"] is None


@pytest.mark.asyncio
async def test_monitoring_vehicle_detail(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)
    await _install_tracker(client, headers, tracker_id, vehicle_id)
    await _set_tracker_telemetry(
        tracker_id,
        last_seen_at=datetime.now(UTC) - timedelta(seconds=90),
        latitude=-22.5,
        longitude=-48.1,
        speed=55,
        course=200,
    )

    response = await client.get(f"{BASE}/monitoring/vehicles/{vehicle_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["customer"]["id"] == customer_id
    assert body["vehicle"]["id"] == vehicle_id
    assert body["tracker"]["id"] == tracker_id
    assert body["health"] == "UNSTABLE"
    assert body["last_seen_at"] is not None
    assert body["latitude"] == pytest.approx(-22.5)
    assert body["longitude"] == pytest.approx(-48.1)
    assert body["speed"] == pytest.approx(55)
    assert body["course"] == 200


@pytest.mark.asyncio
async def test_monitoring_vehicle_detail_not_found(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"{BASE}/monitoring/vehicles/999999999", headers=headers)
    assert response.status_code == 404

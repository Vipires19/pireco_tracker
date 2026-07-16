from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.core.database import db_manager
from app.domains.devices.models import Tracker

BASE = "/api/v1"


async def _login(client: AsyncClient) -> str:
    response = await client.post(
        f"{BASE}/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_dashboard_overview_uses_health_service(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    overview = await client.get(f"{BASE}/dashboard/overview", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert "clients" in body
    assert "vehicles" in body
    assert "online" in body
    assert "offline" in body
    assert "unstable" in body
    assert "unknown" in body
    assert body["online"] + body["offline"] + body["unstable"] + body["unknown"] >= 0

    # Contagens do dashboard devem bater com os filtros da listagem de rastreadores.
    online_list = await client.get(f"{BASE}/trackers?health=ONLINE&page_size=1", headers=headers)
    offline_list = await client.get(f"{BASE}/trackers?health=OFFLINE&page_size=1", headers=headers)
    unstable_list = await client.get(f"{BASE}/trackers?health=UNSTABLE&page_size=1", headers=headers)
    unknown_list = await client.get(f"{BASE}/trackers?health=UNKNOWN&page_size=1", headers=headers)

    assert online_list.status_code == 200
    assert offline_list.status_code == 200
    assert unstable_list.status_code == 200
    assert unknown_list.status_code == 200

    assert body["online"] == online_list.json()["total"]
    assert body["offline"] == offline_list.json()["total"]
    assert body["unstable"] == unstable_list.json()["total"]
    assert body["unknown"] == unknown_list.json()["total"]


@pytest.mark.asyncio
async def test_tracker_response_health_matches_last_seen(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json={
            "imei": f"867{int(datetime.now(UTC).timestamp() * 1000) % 10**12:012d}"[:15],
            "model": "HealthTest",
            "status": "IN_STOCK",
            "origin": "MANUAL",
        },
    )
    assert create.status_code == 201
    tracker_id = create.json()["id"]
    assert create.json()["health_status"] == "UNKNOWN"

    async for session in db_manager.get_session():
        await session.execute(
            update(Tracker)
            .where(Tracker.id == tracker_id)
            .values(last_seen_at=datetime.now(UTC) - timedelta(seconds=30))
        )
        await session.commit()
        break

    online = await client.get(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert online.json()["health_status"] == "ONLINE"

    async for session in db_manager.get_session():
        await session.execute(
            update(Tracker)
            .where(Tracker.id == tracker_id)
            .values(last_seen_at=datetime.now(UTC) - timedelta(seconds=120))
        )
        await session.commit()
        break

    unstable = await client.get(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert unstable.json()["health_status"] == "UNSTABLE"

    async for session in db_manager.get_session():
        await session.execute(
            update(Tracker)
            .where(Tracker.id == tracker_id)
            .values(last_seen_at=datetime.now(UTC) - timedelta(seconds=200))
        )
        await session.commit()
        break

    offline = await client.get(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert offline.json()["health_status"] == "OFFLINE"

    await client.delete(f"{BASE}/trackers/{tracker_id}", headers=headers)

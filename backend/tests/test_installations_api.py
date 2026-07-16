import random
import time

import pytest
from httpx import AsyncClient

BASE = "/api/v1"


def _unique_imei() -> str:
    suffix = int(time.time() * 1_000_000) % 10**12
    return f"867{suffix:012d}"[:15].ljust(15, "0")


def _unique_document() -> str:
    return f"9{int(time.time() * 1000) % 10**10:010d}"


def _unique_plate() -> str:
    return f"TST{random.randint(0, 9)}{chr(65 + random.randint(0, 25))}{random.randint(0, 99):02d}"


async def _login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        f"{BASE}/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _create_customer(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.post(
        f"{BASE}/customers",
        headers=headers,
        json={
            "full_name": f"Cliente Instalação {int(time.time())}",
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
        json={"customer_id": customer_id, "plate": _unique_plate()},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_tracker(client: AsyncClient, headers: dict[str, str], imei: str | None = None) -> int:
    response = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json={
            "imei": imei or _unique_imei(),
            "model": "GT06N",
            "manufacturer": "Concox",
            "status": "IN_STOCK",
            "origin": "MANUAL",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _installation_payload(tracker_id: int, vehicle_id: int, **extra: object) -> dict:
    payload = {
        "tracker_id": tracker_id,
        "vehicle_id": vehicle_id,
        "installation_type": "PRIMARY",
        "checklist": {
            "power_connected": True,
            "gps_ok": True,
            "gsm_ok": True,
            "ignition_ok": False,
            "blocking_ok": False,
            "test_drive_completed": False,
            "customer_present": True,
        },
        "complete": True,
    }
    payload.update(extra)
    return payload


@pytest.mark.asyncio
async def test_installations_requires_jwt(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/installations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_installations_crud_flow(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)

    create = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_id, vehicle_id),
    )
    assert create.status_code == 201, create.text
    body = create.json()
    installation_id = body["id"]
    assert body["status"] == "INSTALLED"
    assert body["installation_type"] == "PRIMARY"
    assert body["tracker"]["id"] == tracker_id
    assert body["vehicle"]["id"] == vehicle_id
    assert body["customer"]["id"] == customer_id

    listed = await client.get(f"{BASE}/installations?vehicle_id={vehicle_id}", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    got = await client.get(f"{BASE}/installations/{installation_id}", headers=headers)
    assert got.status_code == 200

    updated = await client.put(
        f"{BASE}/installations/{installation_id}",
        headers=headers,
        json={
            "installation_notes": "Instalação revisada",
            "checklist": {
                "power_connected": True,
                "gps_ok": True,
                "gsm_ok": True,
                "ignition_ok": True,
                "blocking_ok": True,
                "test_drive_completed": True,
                "customer_present": True,
            },
        },
    )
    assert updated.status_code == 200
    assert updated.json()["installation_notes"] == "Instalação revisada"
    assert updated.json()["ignition_ok"] is True

    tracker = await client.get(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert tracker.status_code == 200
    assert tracker.json()["status"] == "INSTALLED"


@pytest.mark.asyncio
async def test_installations_duplicate_tracker(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_a = await _create_vehicle(client, headers, customer_id)
    vehicle_b = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)

    first = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_id, vehicle_a),
    )
    assert first.status_code == 201

    second = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_id, vehicle_b),
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "tracker_already_assigned"


@pytest.mark.asyncio
async def test_installations_primary_unique_per_vehicle(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_a = await _create_tracker(client, headers)
    tracker_b = await _create_tracker(client, headers)

    first = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_a, vehicle_id, installation_type="PRIMARY"),
    )
    assert first.status_code == 201

    second = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_b, vehicle_id, installation_type="PRIMARY"),
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "vehicle_primary_exists"


@pytest.mark.asyncio
async def test_installations_allows_multiple_bait(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_a = await _create_tracker(client, headers)
    tracker_b = await _create_tracker(client, headers)

    primary = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_a, vehicle_id, installation_type="PRIMARY"),
    )
    assert primary.status_code == 201

    bait = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_b, vehicle_id, installation_type="BAIT"),
    )
    assert bait.status_code == 201
    assert bait.json()["installation_type"] == "BAIT"


@pytest.mark.asyncio
async def test_installations_blocks_non_installable_tracker(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)

    await client.patch(
        f"{BASE}/trackers/{tracker_id}/status",
        headers=headers,
        json={"status": "LOST"},
    )

    response = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_id, vehicle_id),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "tracker_not_installable"


@pytest.mark.asyncio
async def test_installations_finish_endpoint(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)

    create = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_id, vehicle_id, complete=False),
    )
    assert create.status_code == 201
    installation_id = create.json()["id"]
    assert create.json()["status"] == "IN_PROGRESS"

    finished = await client.patch(
        f"{BASE}/installations/{installation_id}/finish",
        headers=headers,
        json={"installation_notes": "Concluída em campo"},
    )
    assert finished.status_code == 200
    assert finished.json()["status"] == "INSTALLED"
    assert finished.json()["installation_notes"] == "Concluída em campo"


@pytest.mark.asyncio
async def test_tracker_in_stock_releases_active_installation(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)

    create = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_id, vehicle_id),
    )
    assert create.status_code == 201

    to_stock = await client.patch(
        f"{BASE}/trackers/{tracker_id}/status",
        headers=headers,
        json={"status": "IN_STOCK"},
    )
    assert to_stock.status_code == 200
    assert to_stock.json()["status"] == "IN_STOCK"

    active = await client.get(
        f"{BASE}/installations?tracker_id={tracker_id}&active_only=true",
        headers=headers,
    )
    assert active.status_code == 200
    assert active.json()["total"] == 0


@pytest.mark.asyncio
async def test_installations_rejects_non_installable_tracker_status(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)

    await client.patch(
        f"{BASE}/trackers/{tracker_id}/status",
        headers=headers,
        json={"status": "MAINTENANCE"},
    )

    response = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_id, vehicle_id),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "tracker_not_installable"


@pytest.mark.asyncio
async def test_installations_remove_preserves_history(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    vehicle_id = await _create_vehicle(client, headers, customer_id)
    tracker_id = await _create_tracker(client, headers)

    create = await client.post(
        f"{BASE}/installations",
        headers=headers,
        json=_installation_payload(tracker_id, vehicle_id),
    )
    assert create.status_code == 201
    installation_id = create.json()["id"]

    removed = await client.put(
        f"{BASE}/installations/{installation_id}",
        headers=headers,
        json={"status": "REMOVED", "removal_reason": "Troca de equipamento"},
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "REMOVED"
    assert removed.json()["removal_reason"] == "Troca de equipamento"
    assert removed.json()["removed_at"] is not None

    history = await client.get(f"{BASE}/installations/{installation_id}", headers=headers)
    assert history.status_code == 200
    assert history.json()["status"] == "REMOVED"

    tracker = await client.get(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert tracker.json()["status"] == "IN_STOCK"

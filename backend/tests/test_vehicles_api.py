import random
import time

import pytest
from httpx import AsyncClient

from app.core.database import db_manager
from app.domains.fleet.models import VehicleAuditAction
from app.domains.fleet.repositories import VehicleAuditRepository

BASE = "/api/v1"


def _unique_plate() -> str:
    return f"TST{random.randint(0, 9)}{chr(65 + random.randint(0, 25))}{random.randint(0, 99):02d}"


def _unique_document() -> str:
    return f"9{int(time.time() * 1000) % 10**10:010d}"


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
            "full_name": f"Cliente Veículos {int(time.time())}",
            "document": _unique_document(),
            "document_type": "CPF",
            "phone": "(11) 98765-4321",
            "city": "São Paulo",
            "state": "SP",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _vehicle_payload(customer_id: int, plate: str, **extra: object) -> dict:
    payload = {
        "customer_id": customer_id,
        "plate": plate,
        "nickname": "Hilux Fazenda",
        "brand": "Toyota",
        "model": "Hilux",
        "category": "TRUCK",
        "fuel": "DIESEL",
    }
    payload.update(extra)
    return payload


@pytest.mark.asyncio
async def test_vehicles_requires_jwt(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/vehicles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_vehicles_rbac_write_forbidden(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.domains.fleet.api import dependencies as fleet_dependencies
    from app.kernel.security.permissions import Permission, role_has_permission

    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    def deny_vehicle_write(role_slug: str, permission: str) -> bool:
        if permission == Permission.VEHICLES_WRITE.value:
            return False
        return role_has_permission(role_slug, permission)

    monkeypatch.setattr(fleet_dependencies, "role_has_permission", deny_vehicle_write)

    read_response = await client.get(f"{BASE}/vehicles", headers=headers)
    assert read_response.status_code == 200

    write_response = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json={
            "customer_id": 1,
            "plate": _unique_plate(),
        },
    )
    assert write_response.status_code == 403
    assert write_response.json()["detail"] == "Insufficient permissions"


@pytest.mark.asyncio
async def test_vehicles_crud_flow(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    plate = _unique_plate()

    create = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json=_vehicle_payload(customer_id, plate),
    )
    assert create.status_code == 201, create.text
    vehicle = create.json()
    vehicle_id = vehicle["id"]
    assert vehicle["plate"] == plate
    assert vehicle["status"] == "ACTIVE"
    assert vehicle["customer_id"] == customer_id

    listed = await client.get(f"{BASE}/vehicles?search=Hilux", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 1
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_pages"] >= 1

    updated = await client.put(
        f"{BASE}/vehicles/{vehicle_id}",
        headers=headers,
        json=_vehicle_payload(customer_id, plate, nickname="Caminhão 01", brand="Volvo"),
    )
    assert updated.status_code == 200
    assert updated.json()["nickname"] == "Caminhão 01"
    assert updated.json()["brand"] == "Volvo"

    status_patch = await client.patch(
        f"{BASE}/vehicles/{vehicle_id}/status",
        headers=headers,
        json={"status": "IN_STOCK"},
    )
    assert status_patch.status_code == 200
    assert status_patch.json()["status"] == "IN_STOCK"

    deleted = await client.delete(f"{BASE}/vehicles/{vehicle_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"{BASE}/vehicles/{vehicle_id}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "vehicle_not_found"


@pytest.mark.asyncio
async def test_vehicles_duplicate_plate(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    plate = _unique_plate()

    first = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json=_vehicle_payload(customer_id, plate),
    )
    assert first.status_code == 201

    second = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json=_vehicle_payload(customer_id, plate, nickname="Duplicado"),
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "plate_already_exists"


@pytest.mark.asyncio
async def test_vehicles_invalid_customer(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json=_vehicle_payload(999_999_999, _unique_plate()),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "customer_not_found"


@pytest.mark.asyncio
async def test_vehicles_pagination_and_filters(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    plate = _unique_plate()

    create = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json=_vehicle_payload(customer_id, plate, category="TRUCK"),
    )
    assert create.status_code == 201
    vehicle_id = create.json()["id"]

    by_customer = await client.get(
        f"{BASE}/vehicles?customer_id={customer_id}&page_size=5&page=1",
        headers=headers,
    )
    assert by_customer.status_code == 200
    assert by_customer.json()["total"] >= 1

    by_status = await client.get(
        f"{BASE}/vehicles?status=ACTIVE&category=TRUCK",
        headers=headers,
    )
    assert by_status.status_code == 200
    assert any(item["id"] == vehicle_id for item in by_status.json()["items"])

    sorted_desc = await client.get(
        f"{BASE}/vehicles?sort_by=created_at&sort_order=desc&page_size=1",
        headers=headers,
    )
    assert sorted_desc.status_code == 200
    assert sorted_desc.json()["page_size"] == 1

    await client.delete(f"{BASE}/vehicles/{vehicle_id}", headers=headers)


@pytest.mark.asyncio
async def test_vehicles_search_by_customer_name(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    unique_name = f"Cliente Busca {int(time.time())}"
    customer = await client.post(
        f"{BASE}/customers",
        headers=headers,
        json={
            "full_name": unique_name,
            "document": _unique_document(),
            "document_type": "CPF",
            "phone": "(11) 98765-4321",
        },
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]
    plate = _unique_plate()

    create = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json=_vehicle_payload(customer_id, plate),
    )
    assert create.status_code == 201
    vehicle_id = create.json()["id"]

    search = await client.get(
        f"{BASE}/vehicles?search={unique_name.replace(' ', '%20')}",
        headers=headers,
    )
    assert search.status_code == 200
    assert any(item["id"] == vehicle_id for item in search.json()["items"])

    await client.delete(f"{BASE}/vehicles/{vehicle_id}", headers=headers)


@pytest.mark.asyncio
async def test_vehicles_audit_logs(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    plate = _unique_plate()

    create = await client.post(
        f"{BASE}/vehicles",
        headers=headers,
        json=_vehicle_payload(customer_id, plate),
    )
    assert create.status_code == 201
    vehicle_id = create.json()["id"]

    await client.put(
        f"{BASE}/vehicles/{vehicle_id}",
        headers=headers,
        json=_vehicle_payload(customer_id, plate, nickname="Auditado"),
    )
    await client.patch(
        f"{BASE}/vehicles/{vehicle_id}/status",
        headers=headers,
        json={"status": "PENDING_INSTALLATION"},
    )
    await client.delete(f"{BASE}/vehicles/{vehicle_id}", headers=headers)

    async for session in db_manager.get_session():
        audit_repo = VehicleAuditRepository(session)
        logs = await audit_repo.list_by_vehicle_id(vehicle_id)
        actions = [log.action for log in logs]
        assert VehicleAuditAction.CREATED.value in actions
        assert VehicleAuditAction.UPDATED.value in actions
        assert VehicleAuditAction.STATUS_CHANGED.value in actions
        assert VehicleAuditAction.DELETED.value in actions


@pytest.mark.asyncio
async def test_vehicles_delete_missing_returns_404(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.delete(f"{BASE}/vehicles/999999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "vehicle_not_found"

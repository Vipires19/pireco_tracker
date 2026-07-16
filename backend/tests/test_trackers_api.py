import time

import pytest
from httpx import AsyncClient

from app.core.database import db_manager
from app.domains.devices.models import TrackerAuditAction
from app.domains.devices.repositories import TrackerAuditRepository

BASE = "/api/v1"


def _unique_imei() -> str:
    suffix = int(time.time() * 1_000_000) % 10**12
    return f"867{suffix:012d}"[:15].ljust(15, "0")


async def _login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        f"{BASE}/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _tracker_payload(imei: str, **extra: object) -> dict:
    payload = {
        "imei": imei,
        "model": "GT06N",
        "manufacturer": "Concox",
        "firmware": "v1.2.3",
        "carrier": "Vivo",
        "origin": "MANUAL",
    }
    payload.update(extra)
    return payload


@pytest.mark.asyncio
async def test_trackers_requires_jwt(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/trackers")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_trackers_rbac_write_forbidden(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.domains.devices.api import dependencies as devices_dependencies
    from app.kernel.security.permissions import Permission, role_has_permission

    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    def deny_tracker_write(role_slug: str, permission: str) -> bool:
        if permission == Permission.TRACKERS_WRITE.value:
            return False
        return role_has_permission(role_slug, permission)

    monkeypatch.setattr(devices_dependencies, "role_has_permission", deny_tracker_write)

    read_response = await client.get(f"{BASE}/trackers", headers=headers)
    assert read_response.status_code == 200

    write_response = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(_unique_imei()),
    )
    assert write_response.status_code == 403
    assert write_response.json()["detail"] == "Insufficient permissions"


@pytest.mark.asyncio
async def test_trackers_crud_flow(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    imei = _unique_imei()

    create = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei),
    )
    assert create.status_code == 201, create.text
    tracker = create.json()
    tracker_id = tracker["id"]
    assert tracker["imei"] == imei
    assert tracker["status"] == "NEW"
    assert tracker["origin"] == "MANUAL"
    assert tracker["health_status"] == "UNKNOWN"

    listed = await client.get(f"{BASE}/trackers?search=GT06N", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 1
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_pages"] >= 1
    assert "stats" in body

    got = await client.get(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["imei"] == imei

    updated = await client.put(
        f"{BASE}/trackers/{tracker_id}",
        headers=headers,
        json=_tracker_payload(imei, model="GT06E", manufacturer="Coban"),
    )
    assert updated.status_code == 200
    assert updated.json()["model"] == "GT06E"
    assert updated.json()["manufacturer"] == "Coban"

    status_patch = await client.patch(
        f"{BASE}/trackers/{tracker_id}/status",
        headers=headers,
        json={"status": "IN_STOCK"},
    )
    assert status_patch.status_code == 200
    assert status_patch.json()["status"] == "IN_STOCK"

    deleted = await client.delete(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "tracker_not_found"


@pytest.mark.asyncio
async def test_trackers_create_with_origin_and_status(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    imei = _unique_imei()

    create = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei, origin="AUTO_DISCOVERY", status="IN_STOCK"),
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["origin"] == "AUTO_DISCOVERY"
    assert body["status"] == "IN_STOCK"

    await client.delete(f"{BASE}/trackers/{body['id']}", headers=headers)


@pytest.mark.asyncio
async def test_trackers_duplicate_imei(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    imei = _unique_imei()

    first = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei),
    )
    assert first.status_code == 201

    second = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei, model="Duplicado"),
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "imei_already_exists"

    await client.delete(f"{BASE}/trackers/{first.json()['id']}", headers=headers)


@pytest.mark.asyncio
async def test_trackers_soft_delete_allows_recreate_same_imei(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    imei = _unique_imei()

    created = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei),
    )
    assert created.status_code == 201, created.text
    tracker_id = created.json()["id"]

    deleted = await client.delete(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"{BASE}/trackers/{tracker_id}", headers=headers)
    assert missing.status_code == 404

    recreated_response = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei),
    )
    assert recreated_response.status_code == 201, recreated_response.text
    recreated = recreated_response.json()
    assert recreated["imei"] == imei
    assert recreated["id"] != tracker_id

    duplicate = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei, model="Duplicado ativo"),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "imei_already_exists"

    await client.delete(f"{BASE}/trackers/{recreated['id']}", headers=headers)


@pytest.mark.asyncio
async def test_trackers_invalid_imei(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload("123"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_trackers_pagination_and_filters(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    imei = _unique_imei()

    create = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei, origin="IMPORT", carrier="Claro"),
    )
    assert create.status_code == 201
    tracker_id = create.json()["id"]

    by_origin = await client.get(f"{BASE}/trackers?origin=IMPORT&page_size=5", headers=headers)
    assert by_origin.status_code == 200
    assert any(item["id"] == tracker_id for item in by_origin.json()["items"])

    by_health = await client.get(f"{BASE}/trackers?health=UNKNOWN", headers=headers)
    assert by_health.status_code == 200

    by_carrier = await client.get(f"{BASE}/trackers?carrier=Claro", headers=headers)
    assert by_carrier.status_code == 200
    assert any(item["id"] == tracker_id for item in by_carrier.json()["items"])

    sorted_desc = await client.get(
        f"{BASE}/trackers?sort_by=created_at&sort_order=desc&page_size=1",
        headers=headers,
    )
    assert sorted_desc.status_code == 200
    assert sorted_desc.json()["page_size"] == 1

    await client.delete(f"{BASE}/trackers/{tracker_id}", headers=headers)


@pytest.mark.asyncio
async def test_trackers_audit_logs(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    imei = _unique_imei()

    create = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei),
    )
    assert create.status_code == 201
    tracker_id = create.json()["id"]

    await client.put(
        f"{BASE}/trackers/{tracker_id}",
        headers=headers,
        json=_tracker_payload(imei, model="Auditado"),
    )
    await client.patch(
        f"{BASE}/trackers/{tracker_id}/status",
        headers=headers,
        json={"status": "MAINTENANCE"},
    )
    await client.delete(f"{BASE}/trackers/{tracker_id}", headers=headers)

    async for session in db_manager.get_session():
        audit_repo = TrackerAuditRepository(session)
        logs = await audit_repo.list_by_tracker_id(tracker_id)
        actions = [log.action for log in logs]
        assert TrackerAuditAction.CREATED.value in actions
        assert TrackerAuditAction.UPDATED.value in actions
        assert TrackerAuditAction.STATUS_CHANGED.value in actions
        assert TrackerAuditAction.DELETED.value in actions


@pytest.mark.asyncio
async def test_trackers_cannot_set_installed_status_manually(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    imei = _unique_imei()

    create = await client.post(
        f"{BASE}/trackers",
        headers=headers,
        json=_tracker_payload(imei, status="IN_STOCK"),
    )
    assert create.status_code == 201
    tracker_id = create.json()["id"]

    response = await client.patch(
        f"{BASE}/trackers/{tracker_id}/status",
        headers=headers,
        json={"status": "INSTALLED"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "tracker_status_install_forbidden"

    await client.delete(f"{BASE}/trackers/{tracker_id}", headers=headers)


@pytest.mark.asyncio
async def test_trackers_delete_missing_returns_404(client: AsyncClient) -> None:
    token = await _login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.delete(f"{BASE}/trackers/999999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "tracker_not_found"

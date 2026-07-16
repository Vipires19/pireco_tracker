import time

import pytest
from httpx import AsyncClient

BASE = "/api/v1"


def _unique_document() -> str:
    return f"9{int(time.time() * 1000) % 10**10:010d}"


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
            "full_name": f"Cliente Portal {int(time.time())}",
            "document": _unique_document(),
            "document_type": "CPF",
            "phone": "(11) 98765-4321",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _user_payload(customer_id: int, email: str, **extra: object) -> dict:
    payload = {
        "customer_id": customer_id,
        "full_name": "Operador Portal",
        "email": email,
        "password": "senha12345",
        "password_confirm": "senha12345",
        "role": "OPERATOR",
        "status": "ACTIVE",
        "must_change_password": True,
    }
    payload.update(extra)
    return payload


@pytest.mark.asyncio
async def test_customer_users_crud(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    email = f"portal.user.{int(time.time())}@example.com"

    create = await client.post(
        f"{BASE}/customer-users",
        headers=headers,
        json=_user_payload(customer_id, email),
    )
    assert create.status_code == 201, create.text
    user = create.json()
    user_id = user["id"]
    assert user["customer_id"] == customer_id
    assert user["role"] == "OPERATOR"
    assert user["must_change_password"] is True
    assert user["last_login_at"] is None

    listed = await client.get(
        f"{BASE}/customer-users",
        headers=headers,
        params={"customer_id": customer_id},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = await client.put(
        f"{BASE}/customer-users/{user_id}",
        headers=headers,
        json={"full_name": "Admin Cliente", "role": "CLIENT_ADMIN", "must_change_password": False},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "CLIENT_ADMIN"
    assert updated.json()["must_change_password"] is False
    assert updated.json()["full_name"] == "Admin Cliente"

    status_patch = await client.patch(
        f"{BASE}/customer-users/{user_id}/status",
        headers=headers,
        json={"status": "INACTIVE"},
    )
    assert status_patch.status_code == 200
    assert status_patch.json()["status"] == "INACTIVE"

    reset = await client.post(
        f"{BASE}/customer-users/{user_id}/reset-password",
        headers=headers,
        json={
            "password": "novaSenha99",
            "password_confirm": "novaSenha99",
            "must_change_password": True,
        },
    )
    assert reset.status_code == 200
    assert reset.json()["must_change_password"] is True

    deleted = await client.delete(f"{BASE}/customer-users/{user_id}", headers=headers)
    assert deleted.status_code == 204

    listed_after = await client.get(
        f"{BASE}/customer-users",
        headers=headers,
        params={"customer_id": customer_id},
    )
    assert listed_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_customer_users_password_mismatch(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    email = f"mismatch.{int(time.time())}@example.com"

    response = await client.post(
        f"{BASE}/customer-users",
        headers=headers,
        json=_user_payload(
            customer_id,
            email,
            password="senha12345",
            password_confirm="outraSenha",
        ),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_customer_users_must_change_password_false(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    email = f"nochg.{int(time.time())}@example.com"

    create = await client.post(
        f"{BASE}/customer-users",
        headers=headers,
        json=_user_payload(customer_id, email, must_change_password=False),
    )
    assert create.status_code == 201
    assert create.json()["must_change_password"] is False
    await client.delete(f"{BASE}/customer-users/{create.json()['id']}", headers=headers)


@pytest.mark.asyncio
async def test_customer_users_duplicate_email(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    email = f"dup.user.{int(time.time())}@example.com"

    first = await client.post(
        f"{BASE}/customer-users",
        headers=headers,
        json=_user_payload(customer_id, email),
    )
    assert first.status_code == 201

    second = await client.post(
        f"{BASE}/customer-users",
        headers=headers,
        json=_user_payload(customer_id, email, full_name="User B"),
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "customer_user_email_exists"

    await client.delete(f"{BASE}/customer-users/{first.json()['id']}", headers=headers)

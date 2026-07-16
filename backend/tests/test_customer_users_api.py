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
            "full_name": f"Cliente Users {int(time.time())}",
            "document": _unique_document(),
            "document_type": "CPF",
            "phone": "(11) 98765-4321",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_customer_users_crud(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    email = f"portal.user.{int(time.time())}@example.com"

    create = await client.post(
        f"{BASE}/customers/{customer_id}/users",
        headers=headers,
        json={
            "full_name": "Operador Portal",
            "email": email,
            "password": "senha12345",
            "role": "OPERATOR",
            "status": "ACTIVE",
        },
    )
    assert create.status_code == 201, create.text
    user = create.json()
    user_id = user["id"]
    assert user["customer_id"] == customer_id
    assert user["role"] == "OPERATOR"

    listed = await client.get(f"{BASE}/customers/{customer_id}/users", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = await client.put(
        f"{BASE}/customers/{customer_id}/users/{user_id}",
        headers=headers,
        json={"role": "CLIENT_ADMIN", "status": "INACTIVE"},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "CLIENT_ADMIN"
    assert updated.json()["status"] == "INACTIVE"

    deleted = await client.delete(f"{BASE}/customers/{customer_id}/users/{user_id}", headers=headers)
    assert deleted.status_code == 204

    listed_after = await client.get(f"{BASE}/customers/{customer_id}/users", headers=headers)
    assert listed_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_customer_users_duplicate_email(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = await _create_customer(client, headers)
    email = f"dup.user.{int(time.time())}@example.com"

    first = await client.post(
        f"{BASE}/customers/{customer_id}/users",
        headers=headers,
        json={
            "full_name": "User A",
            "email": email,
            "password": "senha12345",
            "role": "VIEWER",
        },
    )
    assert first.status_code == 201

    second = await client.post(
        f"{BASE}/customers/{customer_id}/users",
        headers=headers,
        json={
            "full_name": "User B",
            "email": email,
            "password": "senha12345",
            "role": "VIEWER",
        },
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "customer_user_email_exists"

    await client.delete(
        f"{BASE}/customers/{customer_id}/users/{first.json()['id']}",
        headers=headers,
    )

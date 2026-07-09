import time

import pytest
from httpx import AsyncClient

BASE = "/api/v1"


async def _login(client: AsyncClient) -> str:
    response = await client.post(
        f"{BASE}/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_customers_crud_flow(client: AsyncClient) -> None:
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    unique_document = f"9{int(time.time() * 1000) % 10**10:010d}"

    create = await client.post(
        f"{BASE}/customers",
        headers=headers,
        json={
            "full_name": "Cliente Teste Sprint 2",
            "document": unique_document,
            "document_type": "CPF",
            "phone": "(11) 98765-4321",
            "email": "cliente.teste@example.com",
            "city": "São Paulo",
            "state": "SP",
        },
    )
    assert create.status_code == 201, create.text
    customer = create.json()
    customer_id = customer["id"]
    assert customer["document"] == unique_document
    assert customer["status"] == "ACTIVE"

    listed = await client.get(f"{BASE}/customers?search=Cliente%20Teste", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = await client.put(
        f"{BASE}/customers/{customer_id}",
        headers=headers,
        json={
            "full_name": "Cliente Teste Atualizado",
            "document": unique_document,
            "document_type": "CPF",
            "phone": "(11) 98765-4321",
            "email": "cliente.teste@example.com",
            "city": "Campinas",
            "state": "SP",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Campinas"

    status_patch = await client.patch(
        f"{BASE}/customers/{customer_id}/status",
        headers=headers,
        json={"status": "INACTIVE"},
    )
    assert status_patch.status_code == 200
    assert status_patch.json()["status"] == "INACTIVE"

    deleted = await client.delete(f"{BASE}/customers/{customer_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"{BASE}/customers/{customer_id}", headers=headers)
    assert missing.status_code == 404

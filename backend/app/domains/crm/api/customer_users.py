from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.api.dependencies import require_clients_read, require_clients_write
from app.domains.crm.schemas import (
    CustomerUserCreate,
    CustomerUserListResponse,
    CustomerUserResponse,
    CustomerUserUpdate,
)
from app.domains.crm.services import CustomerUserService
from app.domains.identity.models import User
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/customers/{customer_id}/users", tags=["crm"])


def _handle_service_error(exc: ValueError) -> HTTPException:
    code = str(exc)
    status_map = {
        "customer_not_found": status.HTTP_404_NOT_FOUND,
        "customer_user_not_found": status.HTTP_404_NOT_FOUND,
        "customer_user_email_exists": status.HTTP_409_CONFLICT,
    }
    return HTTPException(
        status_code=status_map.get(code, status.HTTP_400_BAD_REQUEST),
        detail=code,
    )


@router.get("", response_model=CustomerUserListResponse)
async def list_customer_users(
    customer_id: int,
    _: User = Depends(require_clients_read),
    session: AsyncSession = Depends(get_db),
) -> CustomerUserListResponse:
    service = CustomerUserService(session)
    try:
        return await service.list_users(customer_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.post("", response_model=CustomerUserResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_user(
    customer_id: int,
    payload: CustomerUserCreate,
    _: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerUserResponse:
    service = CustomerUserService(session)
    try:
        return await service.create_user(customer_id, payload)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.put("/{user_id}", response_model=CustomerUserResponse)
async def update_customer_user(
    customer_id: int,
    user_id: int,
    payload: CustomerUserUpdate,
    _: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerUserResponse:
    service = CustomerUserService(session)
    try:
        return await service.update_user(customer_id, user_id, payload)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_user(
    customer_id: int,
    user_id: int,
    _: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = CustomerUserService(session)
    try:
        await service.delete_user(customer_id, user_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc

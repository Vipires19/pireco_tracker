from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.api.dependencies import require_clients_read, require_clients_write
from app.domains.crm.schemas import (
    CustomerUserCreate,
    CustomerUserListResponse,
    CustomerUserResponse,
    CustomerUserUpdate,
)
from app.domains.crm.schemas.customer_user import (
    CustomerUserResetPassword,
    CustomerUserStatusUpdate,
)
from app.domains.crm.services import CustomerUserService
from app.domains.identity.models import User
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/customer-users", tags=["crm"])


def _handle_service_error(exc: ValueError) -> HTTPException:
    code = str(exc)
    # Pydantic model_validator raises ValueError('passwords_do_not_match') wrapped.
    if "passwords_do_not_match" in code:
        code = "passwords_do_not_match"
    status_map = {
        "customer_not_found": status.HTTP_404_NOT_FOUND,
        "customer_user_not_found": status.HTTP_404_NOT_FOUND,
        "customer_user_email_exists": status.HTTP_409_CONFLICT,
        "passwords_do_not_match": status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(
        status_code=status_map.get(code, status.HTTP_400_BAD_REQUEST),
        detail=code,
    )


@router.get("", response_model=CustomerUserListResponse)
async def list_customer_users(
    customer_id: int | None = Query(default=None, ge=1),
    _: User = Depends(require_clients_read),
    session: AsyncSession = Depends(get_db),
) -> CustomerUserListResponse:
    service = CustomerUserService(session)
    try:
        return await service.list_users(customer_id=customer_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.post("", response_model=CustomerUserResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_user(
    payload: CustomerUserCreate,
    _: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerUserResponse:
    service = CustomerUserService(session)
    try:
        return await service.create_user(payload)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.put("/{user_id}", response_model=CustomerUserResponse)
async def update_customer_user(
    user_id: int,
    payload: CustomerUserUpdate,
    _: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerUserResponse:
    service = CustomerUserService(session)
    try:
        return await service.update_user(user_id, payload)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.patch("/{user_id}/status", response_model=CustomerUserResponse)
async def update_customer_user_status(
    user_id: int,
    payload: CustomerUserStatusUpdate,
    _: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerUserResponse:
    service = CustomerUserService(session)
    try:
        return await service.update_status(user_id, payload)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.post("/{user_id}/reset-password", response_model=CustomerUserResponse)
async def reset_customer_user_password(
    user_id: int,
    payload: CustomerUserResetPassword,
    _: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerUserResponse:
    service = CustomerUserService(session)
    try:
        return await service.reset_password(user_id, payload)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_user(
    user_id: int,
    _: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = CustomerUserService(session)
    try:
        await service.delete_user(user_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc

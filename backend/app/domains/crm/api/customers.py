from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.api.dependencies import require_clients_read, require_clients_write
from app.domains.crm.models import CustomerStatus
from app.domains.crm.schemas import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerSortField,
    CustomerStatusUpdate,
    CustomerUpdate,
    SortOrder,
)
from app.domains.crm.services import CustomerService
from app.domains.identity.models import User
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/customers", tags=["crm"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _handle_service_error(exc: ValueError) -> HTTPException:
    code = str(exc)
    status_map = {
        "customer_not_found": status.HTTP_404_NOT_FOUND,
        "document_already_exists": status.HTTP_409_CONFLICT,
    }
    return HTTPException(
        status_code=status_map.get(code, status.HTTP_400_BAD_REQUEST),
        detail=code,
    )


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    search: str | None = Query(default=None, max_length=120),
    status_filter: CustomerStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: CustomerSortField = Query(default=CustomerSortField.FULL_NAME),
    sort_order: SortOrder = Query(default=SortOrder.ASC),
    _: User = Depends(require_clients_read),
    session: AsyncSession = Depends(get_db),
) -> CustomerListResponse:
    service = CustomerService(session)
    return await service.list_customers(
        search=search,
        status=status_filter,
        page=page,
        page_size=page_size,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    _: User = Depends(require_clients_read),
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    service = CustomerService(session)
    try:
        customer = await service.get_customer(customer_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return CustomerResponse.model_validate(customer)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    request: Request,
    current_user: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    service = CustomerService(session)
    try:
        customer = await service.create_customer(
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    request: Request,
    current_user: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    service = CustomerService(session)
    try:
        customer = await service.update_customer(
            customer_id,
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return CustomerResponse.model_validate(customer)


@router.patch("/{customer_id}/status", response_model=CustomerResponse)
async def update_customer_status(
    customer_id: int,
    payload: CustomerStatusUpdate,
    request: Request,
    current_user: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    service = CustomerService(session)
    try:
        customer = await service.update_status(
            customer_id,
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    request: Request,
    current_user: User = Depends(require_clients_write),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = CustomerService(session)
    try:
        await service.delete_customer(
            customer_id,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc

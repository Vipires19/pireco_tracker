from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.fleet.api.dependencies import require_vehicles_read, require_vehicles_write
from app.domains.fleet.models import VehicleCategory, VehicleStatus
from app.domains.fleet.schemas import (
    SortOrder,
    VehicleCreate,
    VehicleListResponse,
    VehicleResponse,
    VehicleSortField,
    VehicleStatusUpdate,
    VehicleUpdate,
)
from app.domains.fleet.services import VehicleService
from app.domains.identity.models import User
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/vehicles", tags=["fleet"])


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
        "vehicle_not_found": status.HTTP_404_NOT_FOUND,
        "customer_not_found": status.HTTP_404_NOT_FOUND,
        "plate_already_exists": status.HTTP_409_CONFLICT,
        "chassis_already_exists": status.HTTP_409_CONFLICT,
    }
    return HTTPException(
        status_code=status_map.get(code, status.HTTP_400_BAD_REQUEST),
        detail=code,
    )


@router.get("", response_model=VehicleListResponse)
async def list_vehicles(
    search: str | None = Query(default=None, max_length=120),
    status_filter: VehicleStatus | None = Query(default=None, alias="status"),
    customer_id: int | None = Query(default=None, ge=1),
    category: VehicleCategory | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: VehicleSortField = Query(default=VehicleSortField.PLATE),
    sort_order: SortOrder = Query(default=SortOrder.ASC),
    _: User = Depends(require_vehicles_read),
    session: AsyncSession = Depends(get_db),
) -> VehicleListResponse:
    service = VehicleService(session)
    return await service.list_vehicles(
        customer_id=customer_id,
        search=search,
        status=status_filter,
        category=category.value if category else None,
        page=page,
        page_size=page_size,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
    )


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: int,
    _: User = Depends(require_vehicles_read),
    session: AsyncSession = Depends(get_db),
) -> VehicleResponse:
    service = VehicleService(session)
    try:
        vehicle = await service.get_vehicle(vehicle_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return VehicleResponse.model_validate(vehicle)


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    request: Request,
    current_user: User = Depends(require_vehicles_write),
    session: AsyncSession = Depends(get_db),
) -> VehicleResponse:
    service = VehicleService(session)
    try:
        vehicle = await service.create_vehicle(
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return VehicleResponse.model_validate(vehicle)


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    request: Request,
    current_user: User = Depends(require_vehicles_write),
    session: AsyncSession = Depends(get_db),
) -> VehicleResponse:
    service = VehicleService(session)
    try:
        vehicle = await service.update_vehicle(
            vehicle_id,
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return VehicleResponse.model_validate(vehicle)


@router.patch("/{vehicle_id}/status", response_model=VehicleResponse)
async def update_vehicle_status(
    vehicle_id: int,
    payload: VehicleStatusUpdate,
    request: Request,
    current_user: User = Depends(require_vehicles_write),
    session: AsyncSession = Depends(get_db),
) -> VehicleResponse:
    service = VehicleService(session)
    try:
        vehicle = await service.update_status(
            vehicle_id,
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return VehicleResponse.model_validate(vehicle)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: int,
    request: Request,
    current_user: User = Depends(require_vehicles_write),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = VehicleService(session)
    try:
        await service.delete_vehicle(
            vehicle_id,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc

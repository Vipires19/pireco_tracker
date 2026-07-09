from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.models import InstallationStatus, InstallationType
from app.domains.identity.models import User
from app.domains.operations.api.dependencies import (
    require_installations_read,
    require_installations_write,
)
from app.domains.operations.schemas import (
    InstallationCreate,
    InstallationFinish,
    InstallationListResponse,
    InstallationResponse,
    InstallationSortField,
    InstallationUpdate,
    SortOrder,
)
from app.domains.operations.services import InstallationService
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/installations", tags=["operations"])


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
        "installation_not_found": status.HTTP_404_NOT_FOUND,
        "tracker_not_found": status.HTTP_404_NOT_FOUND,
        "vehicle_not_found": status.HTTP_404_NOT_FOUND,
        "technician_not_found": status.HTTP_404_NOT_FOUND,
        "tracker_already_assigned": status.HTTP_409_CONFLICT,
        "vehicle_primary_exists": status.HTTP_409_CONFLICT,
        "tracker_not_installable": status.HTTP_400_BAD_REQUEST,
        "installation_not_editable": status.HTTP_400_BAD_REQUEST,
        "installation_cannot_finish": status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(
        status_code=status_map.get(code, status.HTTP_400_BAD_REQUEST),
        detail=code,
    )


@router.get("", response_model=InstallationListResponse)
async def list_installations(
    search: str | None = Query(default=None, max_length=120),
    status_filter: InstallationStatus | None = Query(default=None, alias="status"),
    installation_type: InstallationType | None = Query(default=None),
    vehicle_id: int | None = Query(default=None, ge=1),
    tracker_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    active_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: InstallationSortField = Query(default=InstallationSortField.INSTALLED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    _: User = Depends(require_installations_read),
    session: AsyncSession = Depends(get_db),
) -> InstallationListResponse:
    service = InstallationService(session)
    return await service.list_installations(
        search=search,
        status=status_filter,
        installation_type=installation_type,
        vehicle_id=vehicle_id,
        tracker_id=tracker_id,
        customer_id=customer_id,
        active_only=active_only,
        page=page,
        page_size=page_size,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
    )


@router.get("/{installation_id}", response_model=InstallationResponse)
async def get_installation(
    installation_id: int,
    _: User = Depends(require_installations_read),
    session: AsyncSession = Depends(get_db),
) -> InstallationResponse:
    service = InstallationService(session)
    try:
        return await service.get_installation(installation_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.post("", response_model=InstallationResponse, status_code=status.HTTP_201_CREATED)
async def create_installation(
    payload: InstallationCreate,
    request: Request,
    current_user: User = Depends(require_installations_write),
    session: AsyncSession = Depends(get_db),
) -> InstallationResponse:
    service = InstallationService(session)
    try:
        return await service.create_installation(
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.put("/{installation_id}", response_model=InstallationResponse)
async def update_installation(
    installation_id: int,
    payload: InstallationUpdate,
    request: Request,
    current_user: User = Depends(require_installations_write),
    session: AsyncSession = Depends(get_db),
) -> InstallationResponse:
    service = InstallationService(session)
    try:
        return await service.update_installation(
            installation_id,
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc


@router.patch("/{installation_id}/finish", response_model=InstallationResponse)
async def finish_installation(
    installation_id: int,
    payload: InstallationFinish,
    request: Request,
    current_user: User = Depends(require_installations_write),
    session: AsyncSession = Depends(get_db),
) -> InstallationResponse:
    service = InstallationService(session)
    try:
        return await service.finish_installation(
            installation_id,
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc

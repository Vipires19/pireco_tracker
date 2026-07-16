from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.api.dependencies import require_trackers_read, require_trackers_write
from app.domains.devices.models import HealthStatus, TrackerOrigin, TrackerStatus
from app.domains.devices.schemas import (
    SortOrder,
    TrackerCreate,
    TrackerListResponse,
    TrackerResponse,
    TrackerSortField,
    TrackerStatusUpdate,
    TrackerUpdate,
)
from app.domains.devices.services import TrackerService
from app.domains.identity.models import User
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/trackers", tags=["devices"])


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
        "tracker_not_found": status.HTTP_404_NOT_FOUND,
        "imei_already_exists": status.HTTP_409_CONFLICT,
        "tracker_has_active_assignment": status.HTTP_409_CONFLICT,
    }
    return HTTPException(
        status_code=status_map.get(code, status.HTTP_400_BAD_REQUEST),
        detail=code,
    )


@router.get("", response_model=TrackerListResponse)
async def list_trackers(
    search: str | None = Query(default=None, max_length=120),
    status_filter: TrackerStatus | None = Query(default=None, alias="status"),
    origin: TrackerOrigin | None = Query(default=None),
    health: HealthStatus | None = Query(default=None),
    carrier: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: TrackerSortField = Query(default=TrackerSortField.CREATED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    _: User = Depends(require_trackers_read),
    session: AsyncSession = Depends(get_db),
) -> TrackerListResponse:
    service = TrackerService(session)
    return await service.list_trackers(
        search=search,
        status=status_filter,
        origin=origin.value if origin else None,
        health=health.value if health else None,
        carrier=carrier,
        page=page,
        page_size=page_size,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
    )


@router.get("/{tracker_id}", response_model=TrackerResponse)
async def get_tracker(
    tracker_id: int,
    _: User = Depends(require_trackers_read),
    session: AsyncSession = Depends(get_db),
) -> TrackerResponse:
    service = TrackerService(session)
    try:
        tracker = await service.get_tracker(tracker_id)
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return service.serialize(tracker)


@router.post("", response_model=TrackerResponse, status_code=status.HTTP_201_CREATED)
async def create_tracker(
    payload: TrackerCreate,
    request: Request,
    current_user: User = Depends(require_trackers_write),
    session: AsyncSession = Depends(get_db),
) -> TrackerResponse:
    service = TrackerService(session)
    try:
        tracker = await service.create_tracker(
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return service.serialize(tracker)


@router.put("/{tracker_id}", response_model=TrackerResponse)
async def update_tracker(
    tracker_id: int,
    payload: TrackerUpdate,
    request: Request,
    current_user: User = Depends(require_trackers_write),
    session: AsyncSession = Depends(get_db),
) -> TrackerResponse:
    service = TrackerService(session)
    try:
        tracker = await service.update_tracker(
            tracker_id,
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return service.serialize(tracker)


@router.patch("/{tracker_id}/status", response_model=TrackerResponse)
async def update_tracker_status(
    tracker_id: int,
    payload: TrackerStatusUpdate,
    request: Request,
    current_user: User = Depends(require_trackers_write),
    session: AsyncSession = Depends(get_db),
) -> TrackerResponse:
    service = TrackerService(session)
    try:
        tracker = await service.update_status(
            tracker_id,
            payload,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc
    return service.serialize(tracker)


@router.delete("/{tracker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracker(
    tracker_id: int,
    request: Request,
    current_user: User = Depends(require_trackers_write),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = TrackerService(session)
    try:
        await service.delete_tracker(
            tracker_id,
            user=current_user,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise _handle_service_error(exc) from exc

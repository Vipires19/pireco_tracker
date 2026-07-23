from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.api.dependencies import get_current_user
from app.domains.identity.models import User
from app.domains.monitoring.schemas.vehicle import MonitoringVehicleDetail, MonitoringVehicleItem
from app.domains.monitoring.services.monitoring_service import MonitoringService
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def get_monitoring_service(session: AsyncSession = Depends(get_db)) -> MonitoringService:
    return MonitoringService(session)


@router.get("/vehicles", response_model=list[MonitoringVehicleItem])
async def list_monitoring_vehicles(
    _: User = Depends(get_current_user),
    service: MonitoringService = Depends(get_monitoring_service),
) -> list[MonitoringVehicleItem]:
    return await service.list_vehicles()


@router.get("/vehicles/{vehicle_id}", response_model=MonitoringVehicleDetail)
async def get_monitoring_vehicle(
    vehicle_id: int,
    _: User = Depends(get_current_user),
    service: MonitoringService = Depends(get_monitoring_service),
) -> MonitoringVehicleDetail:
    return await service.get_vehicle(vehicle_id)

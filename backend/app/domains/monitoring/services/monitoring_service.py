from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.health import resolve_health_status
from app.domains.monitoring.repositories.monitoring_repository import MonitoringRepository
from app.domains.monitoring.schemas.vehicle import (
    MonitoringCustomerInfo,
    MonitoringTrackerInfo,
    MonitoringVehicleDetail,
    MonitoringVehicleInfo,
    MonitoringVehicleItem,
)


class MonitoringService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = MonitoringRepository(session)

    async def list_vehicles(self) -> list[MonitoringVehicleItem]:
        rows = await self._repository.list_installed_vehicles()
        return [self._to_list_item(tracker, vehicle, customer) for _, tracker, vehicle, customer in rows]

    async def get_vehicle(self, vehicle_id: int) -> MonitoringVehicleDetail:
        row = await self._repository.get_installed_vehicle(vehicle_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Veículo instalado não encontrado",
            )
        _, tracker, vehicle, customer = row
        health = resolve_health_status(tracker.last_seen_at)
        return MonitoringVehicleDetail(
            customer=MonitoringCustomerInfo.model_validate(customer),
            vehicle=MonitoringVehicleInfo.model_validate(vehicle),
            tracker=MonitoringTrackerInfo.model_validate(tracker),
            health=health,
            last_seen_at=tracker.last_seen_at,
            latitude=tracker.last_latitude,
            longitude=tracker.last_longitude,
            speed=tracker.last_speed,
            course=tracker.last_course,
            gps_time=tracker.last_gps_time,
        )

    @staticmethod
    def _to_list_item(tracker, vehicle, customer) -> MonitoringVehicleItem:
        return MonitoringVehicleItem(
            vehicle_id=vehicle.id,
            plate=vehicle.plate,
            model=vehicle.model,
            customer_name=customer.full_name,
            tracker_id=tracker.id,
            tracker_imei=tracker.imei,
            health=resolve_health_status(tracker.last_seen_at),
            latitude=tracker.last_latitude,
            longitude=tracker.last_longitude,
            speed=tracker.last_speed,
            course=tracker.last_course,
            last_seen_at=tracker.last_seen_at,
            gps_time=tracker.last_gps_time,
        )

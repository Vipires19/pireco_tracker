import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.repositories import CustomerRepository
from app.domains.fleet.models import Vehicle, VehicleAuditAction, VehicleStatus
from app.domains.fleet.repositories import VehicleAuditRepository, VehicleRepository
from app.domains.fleet.schemas import (
    VehicleCreate,
    VehicleListResponse,
    VehicleResponse,
    VehicleStats,
    VehicleStatusUpdate,
    VehicleUpdate,
)
from app.domains.identity.models import User
from app.kernel.logger import get_logger

logger = get_logger(__name__)


class VehicleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._vehicles = VehicleRepository(session)
        self._audit = VehicleAuditRepository(session)
        self._customers = CustomerRepository(session)

    async def list_vehicles(
        self,
        *,
        customer_id: int | None,
        search: str | None,
        status: VehicleStatus | None,
        category: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> VehicleListResponse:
        items, total = await self._vehicles.list_vehicles(
            customer_id=customer_id,
            search=search,
            status=status,
            category=category,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        stats = VehicleStats(
            total=await self._vehicles.count_all(),
            active=await self._vehicles.count_by_status(VehicleStatus.ACTIVE),
            inactive=await self._vehicles.count_by_status(VehicleStatus.INACTIVE),
            pending_installation=await self._vehicles.count_by_status(
                VehicleStatus.PENDING_INSTALLATION
            ),
            in_stock=await self._vehicles.count_by_status(VehicleStatus.IN_STOCK),
        )
        total_pages = max(1, math.ceil(total / page_size)) if total else 1
        return VehicleListResponse(
            items=[VehicleResponse.model_validate(v) for v in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            stats=stats,
        )

    async def get_vehicle(self, vehicle_id: int) -> Vehicle:
        vehicle = await self._vehicles.get_by_id(vehicle_id)
        if vehicle is None:
            raise ValueError("vehicle_not_found")
        return vehicle

    async def _ensure_customer_exists(self, customer_id: int) -> None:
        customer = await self._customers.get_by_id(customer_id)
        if customer is None:
            raise ValueError("customer_not_found")

    async def _ensure_unique_identifiers(
        self,
        *,
        plate: str,
        chassis: str | None,
        exclude_id: int | None = None,
    ) -> None:
        existing_plate = await self._vehicles.get_by_plate(plate, exclude_id=exclude_id)
        if existing_plate is not None:
            raise ValueError("plate_already_exists")
        if chassis:
            existing_chassis = await self._vehicles.get_by_chassis(chassis, exclude_id=exclude_id)
            if existing_chassis is not None:
                raise ValueError("chassis_already_exists")

    def _apply_payload(self, vehicle: Vehicle, payload: VehicleCreate | VehicleUpdate) -> None:
        vehicle.customer_id = payload.customer_id
        vehicle.plate = payload.plate
        vehicle.nickname = payload.nickname
        vehicle.brand = payload.brand
        vehicle.model = payload.model
        vehicle.version = payload.version
        vehicle.year_model = payload.year_model
        vehicle.year_manufacture = payload.year_manufacture
        vehicle.color = payload.color
        vehicle.fuel = payload.fuel.value if payload.fuel else None
        vehicle.renavam = payload.renavam
        vehicle.chassis = payload.chassis
        vehicle.category = payload.category.value if payload.category else None
        vehicle.cover_image = str(payload.cover_image) if payload.cover_image else None
        vehicle.odometer = payload.odometer
        vehicle.notes = payload.notes

    async def create_vehicle(
        self,
        payload: VehicleCreate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Vehicle:
        await self._ensure_customer_exists(payload.customer_id)
        await self._ensure_unique_identifiers(plate=payload.plate, chassis=payload.chassis)

        vehicle = Vehicle(status=VehicleStatus.ACTIVE.value)
        self._apply_payload(vehicle, payload)
        created = await self._vehicles.create(vehicle)
        await self._audit.create(
            vehicle_id=created.id,
            user_id=user.id,
            action=VehicleAuditAction.CREATED.value,
            details=f"Veículo criado: {created.plate}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info("Vehicle created id=%s by user_id=%s", created.id, user.id)
        return created

    async def update_vehicle(
        self,
        vehicle_id: int,
        payload: VehicleUpdate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Vehicle:
        vehicle = await self.get_vehicle(vehicle_id)
        await self._ensure_customer_exists(payload.customer_id)
        await self._ensure_unique_identifiers(
            plate=payload.plate,
            chassis=payload.chassis,
            exclude_id=vehicle_id,
        )
        self._apply_payload(vehicle, payload)
        updated = await self._vehicles.update(vehicle)
        await self._audit.create(
            vehicle_id=updated.id,
            user_id=user.id,
            action=VehicleAuditAction.UPDATED.value,
            details=f"Veículo atualizado: {updated.plate}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info("Vehicle updated id=%s by user_id=%s", updated.id, user.id)
        return updated

    async def update_status(
        self,
        vehicle_id: int,
        payload: VehicleStatusUpdate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Vehicle:
        vehicle = await self.get_vehicle(vehicle_id)
        previous = vehicle.status
        vehicle.status = payload.status.value
        updated = await self._vehicles.update(vehicle)
        await self._audit.create(
            vehicle_id=updated.id,
            user_id=user.id,
            action=VehicleAuditAction.STATUS_CHANGED.value,
            details=f"Status alterado de {previous} para {payload.status.value}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info(
            "Vehicle status changed id=%s status=%s by user_id=%s",
            updated.id,
            payload.status.value,
            user.id,
        )
        return updated

    async def delete_vehicle(
        self,
        vehicle_id: int,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        vehicle = await self.get_vehicle(vehicle_id)
        await self._vehicles.soft_delete(vehicle)
        await self._audit.create(
            vehicle_id=vehicle.id,
            user_id=user.id,
            action=VehicleAuditAction.DELETED.value,
            details=f"Veículo excluído (soft delete): {vehicle.plate}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info("Vehicle soft-deleted id=%s by user_id=%s", vehicle.id, user.id)
